"""
Training pipeline for LUNA-CORR neural correspondence models.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import time
import json
import torch
from torch.utils.data import DataLoader

from ..models.correspondence_net import LunarCorrespondenceNet
from ..models.loss import CorrespondenceLoss
from ..data.dataset import LunarCorrespondenceDataset

class LunarTrainer:
    """Trains the correspondence network on synthetic and real lunar image pairs."""

    def __init__(
        self,
        model: Optional[LunarCorrespondenceNet] = None,
        lr: float = 1e-3,
        weight_decay: float = 1e-4,
        device: Optional[str] = None
    ):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = (model or LunarCorrespondenceNet()).to(self.device)
        self.criterion = CorrespondenceLoss().to(self.device)
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=weight_decay)

    def train_epoch(self, dataloader: DataLoader) -> float:
        self.model.train()
        total_loss = 0.0
        n_batches = 0

        for batch in dataloader:
            src = batch["source"].to(self.device)
            ref = batch["reference"].to(self.device)
            H = batch["homography"].to(self.device)
            mask = batch["mask"].to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(src, ref)
            loss_dict = self.criterion(outputs, H, mask)
            loss = loss_dict["loss"]

            if loss.requires_grad and loss.item() > 0:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
                self.optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(1, n_batches)

    def fit(
        self,
        image_paths: List[Path],
        epochs: int = 10,
        batch_size: int = 4,
        crop_size: int = 512,
        output_dir: Path = Path("models/checkpoints")
    ) -> Dict[str, Any]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        dataset = LunarCorrespondenceDataset(image_paths=image_paths, crop_size=crop_size, augment=True)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)

        print(f"\n[LUNA-CORR Trainer] Starting training for {epochs} epochs on device: {self.device}", flush=True)
        print(f"Total dataset samples per epoch: {len(dataset)} (Batch size: {batch_size})", flush=True)

        history = []
        best_loss = float("inf")

        for ep in range(1, epochs + 1):
            t0 = time.time()
            avg_loss = self.train_epoch(dataloader)
            elapsed = time.time() - t0

            print(f"Epoch {ep:02d}/{epochs:02d} - Loss: {avg_loss:.4f} ({elapsed:.1f}s)", flush=True)
            history.append({"epoch": ep, "loss": avg_loss, "time_s": elapsed})

            if avg_loss < best_loss:
                best_loss = avg_loss
                ckpt_path = output_dir / "best_correspondence_net.pt"
                torch.save({
                    "epoch": ep,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "loss": best_loss
                }, ckpt_path)

        # Save final weights and history
        final_path = output_dir / "final_correspondence_net.pt"
        torch.save(self.model.state_dict(), final_path)
        with open(output_dir / "train_history.json", "w") as f:
            json.dump(history, f, indent=2)

        print(f"[LUNA-CORR Trainer] Training complete. Saved model to: {output_dir}")
        return {"best_loss": best_loss, "history": history, "checkpoint": str(output_dir / "best_correspondence_net.pt")}
