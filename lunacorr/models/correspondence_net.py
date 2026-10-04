"""
Deep Neural Correspondence Network for multi-modal lunar image matching.
Uses a lightweight convolutional feature pyramid with dual-softmax correlation.
"""
from typing import Dict, Tuple, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F

class ConvBlock(nn.Module):
    def __init__(self, in_c: int, out_c: int, stride: int = 1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_c, out_c, kernel_size=3, stride=stride, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_c, out_c, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)

class LunarCorrespondenceNet(nn.Module):
    """
    Lightweight feature extractor and correspondence matcher.
    Extracts multi-scale representations invariant to illumination and scale variations.
    """

    def __init__(self, in_channels: int = 1, feat_dim: int = 64):
        super().__init__()
        self.feat_dim = feat_dim

        # Backbone encoder (downsampling 1/8)
        self.layer1 = ConvBlock(in_channels, 32, stride=2)   # 1/2
        self.layer2 = ConvBlock(32, 48, stride=2)            # 1/4
        self.layer3 = ConvBlock(48, feat_dim, stride=2)      # 1/8

        # Projection head with L2 normalization
        self.proj = nn.Conv2d(feat_dim, feat_dim, kernel_size=1)

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extracts L2-normalized feature maps at 1/8 resolution.
        """
        c1 = self.layer1(x)
        c2 = self.layer2(c1)
        c3 = self.layer3(c2)
        feat = self.proj(c3)
        return F.normalize(feat, p=2, dim=1)

    def forward(self, src: torch.Tensor, ref: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass computing feature representations and correlation scores.
        """
        feat_s = self.extract_features(src)
        feat_r = self.extract_features(ref)

        b, c, hs, ws = feat_s.shape
        _, _, hr, wr = feat_r.shape

        # Reshape to (B, C, Ns) and (B, C, Nr)
        s_flat = feat_s.view(b, c, -1)
        r_flat = feat_r.view(b, c, -1)

        # Correlation matrix (B, Ns, Nr)
        sim = torch.bmm(s_flat.transpose(1, 2), r_flat)

        # Dual-softmax matching probabilities
        temp = 0.1
        prob_s = F.softmax(sim / temp, dim=2)
        prob_r = F.softmax(sim / temp, dim=1)
        match_prob = prob_s * prob_r  # Mutual nearest neighbor confidence

        return {
            "feat_source": feat_s,
            "feat_reference": feat_r,
            "similarity": sim,
            "match_probability": match_prob
        }
