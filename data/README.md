# Data Directory Structure

Organize downloaded mission products into the following subdirectories:

```
data/
  ├── ohrc/       # Chandrayaan-2 OHRC products (.xml label + .img data)
  ├── tmc2/       # Chandrayaan-2 TMC-2 products (.xml + .img / GeoTIFF)
  ├── iirs/       # Chandrayaan-2 IIRS hyperspectral cubes (.xml + .img)
  ├── lro_nac/    # Reference LRO NAC products (.IMG / .xml / .tif)
  └── dem/        # Topography DEMs (LOLA DTM or TMC-2 DEM GeoTIFFs)
```

> **Note on Terms:** Chandrayaan-2 data from PRADAN are free for non-profit scientific use. ISRO retains ownership. Never commit raw binary products to version control.
