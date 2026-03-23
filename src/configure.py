import yaml
import json
import os

def configure():
    # Load info.yaml
    with open("info.yaml", "r") as f:
        info = yaml.safe_load(f)
    
    project = info["project"]
    tiles = project.get("tiles", "1x1")
    top_module = project.get("top_module", "tt_um_vga_ca")
    source_files = project.get("source_files", [])
    
    # Load tile_sizes from the repo
    with open("tt/tech/ihp-sg13g2/tile_sizes.yaml", "r") as f:
        tile_sizes = yaml.safe_load(f)
    die_area = tile_sizes.get(tiles, tile_sizes["1x1"])
    
    # Load base config
    # Note: tt tools strip "//" comments, which we will do here too
    with open("src/config.json", "r") as f:
        config = json.load(f)
        config.pop("//", None)
    
    # Update merged config with project-specific values
    config["DESIGN_NAME"] = top_module
    config["VERILOG_FILES"] = [f"dir::{src}" for src in source_files]
    config["DIE_AREA"] = die_area
    config["FP_DEF_TEMPLATE"] = f"dir::../tt/tech/ihp-sg13g2/def/tt_block_{tiles}_pgvdd.def"
    
    # IHP specific pin/layer defaults if not in config.json
    config.setdefault("VDD_PIN", "VPWR")
    config.setdefault("GND_PIN", "VGND")
    config.setdefault("RT_MAX_LAYER", "TopMetal1")

    # Write merged config
    with open("src/config_merged.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Successfully generated src/config_merged.json for {top_module} ({tiles})")

if __name__ == "__main__":
    configure()
