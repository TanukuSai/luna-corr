"""
Correspondence training loss for LunarCorrespondenceNet.
"""
from typing import Dict
import torch
import torch.nn as nn
import torch.nn.functional as F

class CorrespondenceLoss(nn.Module):
    """
    Supervised correspondence loss using ground-truth homography warps.
    """

    def __init__(self, stride: int = 8, pos_threshold_px: float = 4.0):
        super().__init__()
        self.stride = stride
        self.pos_threshold_px = pos_threshold_px

    def forward(
        self,
        outputs: Dict[str, torch.Tensor],
        homographies: torch.Tensor,
        masks: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        feat_s = outputs["feat_source"]
        sim = outputs["similarity"]  # (B, Ns, Nr)
        b, c, hs, ws = feat_s.shape

        device = feat_s.device
        
        # Build coordinate grid at feature scale in original pixel coordinates
        ys, xs = torch.meshgrid(
            torch.arange(hs, device=device, dtype=torch.float32) * self.stride + self.stride / 2,
            torch.arange(ws, device=device, dtype=torch.float32) * self.stride + self.stride / 2,
            indexing="ij"
        )
        grid_s = torch.stack([xs.flatten(), ys.flatten()], dim=1)  # (Ns, 2)

        total_loss = torch.tensor(0.0, device=device, requires_grad=True)
        batch_losses = []

        for i in range(b):
            H = homographies[i]  # 3x3
            # Warp source coordinates to reference frame: x_ref = (H @ x_s)
            ones = torch.ones((len(grid_s), 1), device=device)
            grid_s_h = torch.cat([grid_s, ones], dim=1)  # (Ns, 3)
            warped_h = torch.mm(grid_s_h, H.t())
            warped = warped_h[:, :2] / (warped_h[:, 2:3] + 1e-8)  # (Ns, 2) in ref frame

            # True reference grid
            grid_r = grid_s.clone()  # Assuming same dimensions (Nr, 2)

            # Distance matrix between warped source points and all reference points (Ns, Nr)
            dist = torch.cdist(warped, grid_r)
            min_dist, gt_match_idx = torch.min(dist, dim=1)

            # Positive matches are those within pos_threshold_px
            pos_mask = min_dist < self.pos_threshold_px

            if pos_mask.sum() > 0:
                # Cross-entropy over the similarity logits for positive points
                logits = sim[i, pos_mask] / 0.1  # (N_pos, Nr)
                targets = gt_match_idx[pos_mask]
                ce_loss = F.cross_entropy(logits, targets)
                batch_losses.append(ce_loss)

        if batch_losses:
            loss = torch.stack(batch_losses).mean()
        else:
            loss = torch.tensor(0.0, device=device, requires_grad=True)

        return {"loss": loss}
