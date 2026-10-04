"""
PDS4 XML label parser and image reader for Chandrayaan-2 and reference datasets.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import xml.etree.ElementTree as ET
import numpy as np
import cv2

@dataclass
class LunarProduct:
    product_id: str
    instrument: str  # OHRC, TMC-2, IIRS, LRO_NAC, LOLA_DEM, GENERIC
    image_path: Path
    array: np.ndarray  # float32 normalized [0, 1] or original DN
    mask: np.ndarray   # bool array (True = valid pixel)
    metadata: Dict[str, Any] = field(default_factory=dict)
    sun_angles: Dict[str, Optional[float]] = field(default_factory=dict)
    resolution_m: Optional[float] = None
    original_shape: Tuple[int, int] = (0, 0)

    @property
    def shape(self) -> Tuple[int, int]:
        return self.array.shape[:2]

class PDS4Reader:
    """Reads PDS4 XML labels and planetary data products."""

    @staticmethod
    def parse_xml_label(xml_path: Path) -> Dict[str, Any]:
        """Extracts key metadata from a PDS4 XML label."""
        if not xml_path.exists():
            return {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            # Strip XML namespaces for simplified querying
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            meta: Dict[str, Any] = {}
            
            # Identification
            id_area = root.find(".//Identification_Area")
            if id_area is not None:
                lid = id_area.findtext("logical_identifier")
                meta["logical_identifier"] = lid
                meta["title"] = id_area.findtext("title")
                if lid:
                    meta["product_id"] = lid.split(":")[-1]

            # Instrument identification
            inst = root.findtext(".//Observing_System_Component/name")
            if inst:
                meta["instrument"] = inst
            else:
                for comp in root.findall(".//Observing_System_Component"):
                    t = comp.findtext("type")
                    if t and "Instrument" in t:
                        meta["instrument"] = comp.findtext("name")

            # Sun and viewing geometry
            sun_angles = {}
            for angle_name in ["sun_azimuth_angle", "sun_elevation_angle", "incidence_angle", 
                               "emission_angle", "phase_angle", "solar_zenith_angle"]:
                val = root.findtext(f".//{angle_name}")
                if val:
                    try:
                        sun_angles[angle_name] = float(val)
                    except ValueError:
                        sun_angles[angle_name] = None
                else:
                    sun_angles[angle_name] = None
            meta["sun_angles"] = sun_angles

            # Array dimensions and data types
            axis_elems = root.findall(".//Axis_Array")
            axes = {}
            for ax in axis_elems:
                name = ax.findtext("axis_name")
                elems = ax.findtext("elements")
                if name and elems:
                    try:
                        axes[name] = int(elems)
                    except ValueError:
                        pass
            meta["axes"] = axes

            # Pixel scale / GSD if present
            pixel_res = root.findtext(".//pixel_resolution") or root.findtext(".//spatial_resolution")
            if pixel_res:
                try:
                    meta["resolution_m"] = float(pixel_res)
                except ValueError:
                    pass

            return meta
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def load_product(cls, file_path: Path, max_dim: Optional[int] = None) -> LunarProduct:
        """Loads an image or PDS4 product, returning a LunarProduct instance."""
        file_path = Path(file_path)
        xml_path = file_path.with_suffix(".xml")
        if file_path.suffix.lower() == ".xml":
            xml_path = file_path
            # Look for companion image data
            found_img = False
            for ext in [".img", ".IMG", ".png", ".PNG", ".tif", ".tiff", ".jp2", ".jpg", ".qub"]:
                candidate = file_path.with_suffix(ext)
                if candidate.exists():
                    file_path = candidate
                    found_img = True
                    break
        else:
            xml_path = file_path.with_suffix(".xml")

        meta = cls.parse_xml_label(xml_path) if xml_path.exists() else {}
        
        # Read image data
        raw_img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
        if raw_img is None:
            # Fallback using PIL (e.g. for signed/16-bit JPEG2000 .jp2 or PNG)
            try:
                from PIL import Image
                with Image.open(str(file_path)) as pil_img:
                    raw_img = np.array(pil_img)
            except Exception:
                raw_img = None

        if raw_img is None:
            # Fallback for binary .img / .bin / .qub files
            if file_path.suffix.lower() in [".img", ".bin", ".qub", ".raw"] and "axes" in meta:
                axes = meta["axes"]
                file_size = file_path.stat().st_size
                
                # Check for 3D cube (e.g. IIRS: BAND, LINE, SAMPLE)
                if "BAND" in axes or "band" in axes:
                    bands = axes.get("BAND", axes.get("band", 1))
                    lines = axes.get("LINE", axes.get("Line", axes.get("line", 1)))
                    samples = axes.get("SAMPLE", axes.get("Sample", axes.get("sample", 1)))
                    total_voxels = bands * lines * samples
                    bytes_per_voxel = file_size // total_voxels if total_voxels > 0 else 4
                    dtype = "<f4" if bytes_per_voxel == 4 else "<u2"
                    # Read central reference band (e.g. band 64 or bands//2)
                    ref_band = bands // 2
                    try:
                        # Assuming band-sequential (BSQ) or line-interleaved (BIL)
                        offset = ref_band * lines * samples * bytes_per_voxel
                        raw_img = np.memmap(str(file_path), dtype=dtype, mode="r", offset=offset, shape=(lines, samples))
                        raw_img = np.array(raw_img)
                    except Exception:
                        raw_img = None
                else:
                    # 2D raster (OHRC, TMC-2)
                    rows = axes.get("Line", axes.get("LINE", axes.get("row", 0)))
                    cols = axes.get("Sample", axes.get("SAMPLE", axes.get("column", 0)))
                    if rows > 0 and cols > 0:
                        total_pix = rows * cols
                        bytes_per_pix = file_size // total_pix if total_pix > 0 else 1
                        if bytes_per_pix == 1:
                            dtype = np.uint8
                        elif bytes_per_pix == 2:
                            dtype = "<u2"  # Little-endian uint16
                        elif bytes_per_pix == 4:
                            dtype = "<f4"  # Float32
                        else:
                            dtype = "<u2"

                        try:
                            raw_img = np.fromfile(str(file_path), dtype=dtype, count=total_pix).reshape((rows, cols))
                        except Exception:
                            raw_img = None

        if raw_img is None:
            raise FileNotFoundError(f"Could not load image data from {file_path}")

        # If multi-channel, convert to grayscale float32
        if len(raw_img.shape) == 3:
            raw_img = cv2.cvtColor(raw_img, cv2.COLOR_BGR2GRAY)

        orig_shape = raw_img.shape
        # If max_dim specified and array is massive, pre-decimate to avoid huge RAM and slow INTER_AREA
        if max_dim is not None and max(orig_shape) > (max_dim * 2):
            pre_step = max(orig_shape) // (max_dim * 2)
            raw_img = raw_img[::pre_step, ::pre_step]

        mask = (raw_img > 0) & np.isfinite(raw_img)

        # Normalize to float32 [0, 1] using robust 1st and 99th percentiles
        valid_vals = raw_img[mask]
        if len(valid_vals) > 0:
            vmin, vmax = np.percentile(valid_vals, 1), np.percentile(valid_vals, 99)
            if vmax > vmin:
                norm_img = np.clip((raw_img - vmin) / (vmax - vmin), 0.0, 1.0).astype(np.float32)
            else:
                norm_img = (raw_img / (np.max(raw_img) + 1e-6)).astype(np.float32)
        else:
            norm_img = raw_img.astype(np.float32)

        # Final smooth resize to exact max_dim
        if max_dim is not None and max(norm_img.shape) > max_dim:
            scale = max_dim / max(norm_img.shape)
            norm_img = cv2.resize(norm_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            mask = cv2.resize(mask.astype(np.uint8), (norm_img.shape[1], norm_img.shape[0]), interpolation=cv2.INTER_NEAREST) > 0

        # Infer instrument from path/filename if not in XML
        inst = meta.get("instrument", "UNKNOWN")
        name_lower = file_path.name.lower()
        if "ohr" in name_lower:
            inst = "OHRC"
        elif "tmc" in name_lower:
            inst = "TMC-2"
        elif "iir" in name_lower:
            inst = "IIRS"
        elif "lro" in name_lower or "nac" in name_lower:
            inst = "LRO_NAC"
        elif "lola" in name_lower or "dem" in name_lower:
            inst = "LOLA_DEM"

        res = meta.get("resolution_m")
        if res is None:
            if inst == "OHRC":
                res = 0.25
            elif inst == "TMC-2":
                res = 5.0
            elif inst == "IIRS":
                res = 80.0
            elif inst == "LRO_NAC":
                res = 1.0
            elif inst == "LOLA_DEM":
                res = 1000.0

        return LunarProduct(
            product_id=meta.get("product_id", file_path.stem),
            instrument=inst,
            image_path=file_path,
            array=norm_img,
            mask=mask,
            metadata=meta,
            sun_angles=meta.get("sun_angles", {}),
            resolution_m=res,
            original_shape=orig_shape
        )
