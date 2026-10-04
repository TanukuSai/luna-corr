"""
PyTorch Dataset for lunar multi-modal and synthetic correspondence training.
"""
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import torch
from torch.utils.data import Dataset
import numpy as np
import cv2

from .transforms import LunarAugmentor
from .pds4_reader import PDS4Reader

class LunarCorrespondenceDataset(Dataset):
    """
    Dataset for training correspondence networks on lunar imagery.
    Generates synthetic geometric/photometric pairs on-the-fly with exact ground truth.
    """

    def __init__(
        self,
        image_paths: List[Path],
        crop_size: int = 512,
        augment: bool = True,
        pairs_per_image: int = 5,
        seed: int = 42
    ):
        self.image_paths = [Path(p) for p in image_paths]
        self.crop_size = crop_size
        self.augment = augment
        self.pairs_per_image = pairs_per_image
        self.augmentor = LunarAugmentor(seed=seed)
        
        # Pre-cache or load images
        self.images: List[np.ndarray] = []
        for p in self.image_paths:
            try:
                prod = PDS4Reader.load_product(p, max_dim=2048)
                self.images.append(prod.array)
            except Exception as e:
                print(f"[Dataset] Warning: could not load {p}: {e}")

        if not self.images:
            raise ValueError(f"No valid images loaded from provided paths: {self.image_paths}")

    def __len__(self) -> int:
        return len(self.images) * self.pairs_per_image

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        img_idx = idx % len(self.images)
        full_img = self.images[img_idx]

        h, w = full_img.shape[:2]
        cs = self.crop_size

        # Random square crop if image is larger than crop size
        if h > cs and w > cs:
            top = np.random.randint(0, h - cs)
            left = np.random.randint(0, w - cs)
            crop = full_img[top:top + cs, left:left + cs]
        else:
            crop = cv2.resize(full_img, (cs, cs), interpolation=cv2.INTER_AREA)

        if self.augment:
            pair_data = self.augmentor.generate_pair(
                crop,
                max_rotation_deg=25.0,
                scale_range=(0.8, 1.25),
                max_perspective=0.08,
                simulate_illumination=True
            )
            src = pair_data["source"]
            ref = pair_data["reference"]
            H = pair_data["homography"]
            mask = pair_data["valid_mask"]
        else:
            src = crop
            ref = crop
            H = np.eye(3, dtype=np.float32)
            mask = np.ones_like(crop, dtype=bool)

        # Convert to PyTorch tensors (1, H, W)
        src_t = torch.from_numpy(src).unsqueeze(0).float()
        ref_t = torch.from_numpy(ref).unsqueeze(0).float()
        H_t = torch.from_numpy(H).float()
        mask_t = torch.from_numpy(mask).unsqueeze(0).bool()

        return {
            "source": src_t,
            "reference": ref_t,
            "homography": H_t,
            "mask": mask_t
        }
