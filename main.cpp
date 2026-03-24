#include "fenster.h"
#include "Vproject.h"
#include "verilated.h"

const int PAD = 48;
const int W = 640+PAD*2;
const int H = 480+PAD*2;
struct Bits {
    uint8_t r1:1, g1:1, b1:1, vsync:1, r0:1, g0:1, b0:1, hsync:1;
};


uint32_t bits2channel(uint8_t lo, uint8_t hi, int ch) {
    return (hi*170+lo*85) << (ch*8);
}

int main(int argc, char* argv[]) {
    Fenster f(W, H, "VGA CA demo");
    uint32_t * pixels = f.f.buf;

    Vproject mod;
    mod.ena = 1;
    mod.rst_n = 0;
    mod.eval();
    mod.rst_n = 1;
    mod.eval();

    Bits prev = *(Bits*)(&mod.uo_out);
    int x=0, y=0;
    bool quit = false;
    while (!quit && f.loop(60) && !f.key(27)) {
        while(1) {
            mod.clk = !mod.clk;
            mod.eval();
            Bits v = *(Bits*)(&mod.uo_out);
            if (prev.hsync && !v.hsync) {
                x = 0;
                y += 1;
            }
            bool vsync = prev.vsync && !v.vsync;
            if (vsync) {
                x = 0;
                y = 0;
            }
            if (x<W && y<H) {
                pixels[y*W + x] = bits2channel(v.b0, v.b1, 0) | 
                    bits2channel(v.g0, v.g1, 1) | bits2channel(v.r0, v.r1, 2);
            }
            prev = v;

            x += mod.clk;
            if (vsync) break;
        }
    }
    return 0;
}

