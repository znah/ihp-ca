import re
import sys

def generate_placement():
    with open("src/project.v", "r") as f:
        project_v = f.read()
    
    grid_w_match = re.search(r"parameter\s+GRID_W\s*=\s*(\d+);", project_v)
    if not grid_w_match:
        print("Error: Could not find GRID_W parameter in src/project.v")
        sys.exit(1)
    
    grid_w = int(grid_w_match.group(1))
    print(f"Using GRID_W = {grid_w} from src/project.v")

    pitch_x = 0.480
    row_height = 3.780
    die_start_x = 2.880
    die_width = 202.080
    die_height = 154.980

    site_dff = 27
    site_dly = 9
    
    dff_w = pitch_x * site_dff
    dly_w = pitch_x * site_dly
    block_w = dff_w + dly_w

    cfg = []
    svg = [f''' 
    <svg viewBox="0 0 {die_width} {die_height}" xmlns="http://www.w3.org/2000/svg">
    <style>
        rect {{stroke-width:0.5;}}
        text {{text-anchor: middle; dominant-baseline: central;
               font-size:2px; fill:white; font-family:sans-serif;}}
        .dff {{fill: orange; stroke:#777;}}
        .dly {{fill: green; stroke:#777;}}
    </style>
    <rect x="0" y="0" width="{die_width}" height="{die_height}" fill="none" stroke="red"/>
    ''']

    def cell(x, y, w, h, cls, label, i, orient):
        svg.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}"/>')
        svg.append(f'<text x="{x+w/2}" y="{y+h/2}">{i}</text>')
        cfg.append(f'{label}[{i}] {x:.3f} {y:.3f} {orient}')
    def dff(x, y, label, i, orient):
        cell(x, y, dff_w, row_height, 'dff', label, i, orient)
    def dly(x, y, label, i, orient):
        cell(x, y, dly_w, row_height, 'dly', label, i, orient)
        
    def gen_row(x, row, label, i0, n, flow):
        if flow == 'R':
            orient = "FS" if (row % 2 != 0) else "N"
            step_x = block_w
            dff_x = x
            dly_x = dff_x + dff_w
        elif flow == 'L':
            orient = "S"  if (row % 2 != 0) else "FN"
            step_x = -block_w
            dff_x = x + block_w*n - dff_w
            dly_x = dff_x-dly_w
        y = (row+1)*row_height
        for j in range(n):
            dff(dff_x + j*step_x, y, label+"cells_reg", i+j, orient)
            dly(dly_x + j*step_x, y, label+"cellsbuf_", i+j, orient)

#     u, v = (0.85 if orient in ("S", "FN") else 0.15), (0.85 if orient in ("S", "FS") else 0.15)

    i, row = 0, 0
    while i<grid_w:
        n = 5 if row < 4 else 4
        n = min(n, grid_w-i)
        flip = row % 2 != 0
        gen_row(die_start_x, row, "", i, n, "LR"[flip])
        gen_row(die_width-(block_w*n + die_start_x), row, "first_row_", i, n, "RL"[flip])
        i += n
        row += 1

    # for i in range(0, grid_w, 4):
    #     row = i//4 #+ i//(4*8)
    #     flip = (i//4) % 2 != 0
    #     gen_row(die_start_x, row, "", i, 4, "LR"[flip])
    #     gen_row(die_width-(block_w*4 + die_start_x), row, "first_row_", i, 4, "RL"[flip])




    svg.append('</svg>')
    open("src/placement.cfg", "w").write("\n".join(cfg))
    open("src/placement.svg", "w").write("\n".join(svg))

    # print("Success: Generated placement configuration (placement.cfg) and visual mapping (placement.svg).")

if __name__ == "__main__":
    generate_placement()
