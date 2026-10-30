// SPDX-License-Identifier: GPL-2.0-or-later
// Run the exact platform bridge against a read-only pack before device play.
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
#include "doomstat.h"
static const uint8_t *image;
static uint32_t image_size,clock_ms,buttons;
static uint8_t input_script[32];
static unsigned input_count,input_index;
static uint16_t screen[320*240];
static char error[192];
static jmp_buf bail_out;
// Host-only trace to compare asset cache choices against actual engine reads.
static uint32_t trace[262144][2], trace_used;
void km_doom_init(void);
void km_doom_step(void);
void km_doom_redraw(void);
void D_Display(void);
void NetUpdate(void);
uint32_t km_millis(void) { return clock_ms; }
void km_sleep(uint32_t ms) { clock_ms+=ms; }
uint32_t km_keys(void) { return input_index<input_count ? input_script[input_index++] : buttons; }
__attribute__((noreturn)) void km_fail(const char *message) {
    size_t n=strlen(message);if(n>=sizeof(error))n=sizeof(error)-1;
    memcpy(error,message,n);error[n]=0;longjmp(bail_out,1);
}
__attribute__((noreturn)) void km_exit(void) { km_fail("Game requested exit"); }
void km_flash_read(uint32_t off,void *dst,uint32_t n) {
    if(off>image_size || n>image_size-off)km_fail("Host pack read out of range");
    if(trace_used<262144) { trace[trace_used][0]=off;trace[trace_used++][1]=n; }
    memcpy(dst,image+off,n);
}
void km_column(int x,int y,int h,const uint16_t *pixels) {
    if(x<0 || x>=320 || y<0 || h<0 || y+h>240)km_fail("Host LCD bounds");
    for(int i=0;i<h;i++)screen[(y+i)*320+x]=pixels[i];
}
__declspec(dllexport) int km_host_init(const uint8_t *data,uint32_t n) {
    image=data;image_size=n;clock_ms=0;
    if(setjmp(bail_out))return -1;km_doom_init();return 0;
}
__declspec(dllexport) int km_host_step(uint32_t keys) {
    clock_ms+=29;buttons=keys;
    if(setjmp(bail_out))return -1;km_doom_step();return 0;
}
// Exercise queued edges at the real engine's full tic-command buffer boundary.
__declspec(dllexport) int km_host_input_script(const uint8_t *states,uint32_t n) {
    if(n>sizeof(input_script))return -1;
    memcpy(input_script,states,n);input_count=n;input_index=0;return 0;
}
__declspec(dllexport) uint32_t km_host_input_pending(void) { return input_count-input_index; }
__declspec(dllexport) int km_host_build_tics(uint32_t ms) {
    clock_ms+=ms;
    if(setjmp(bail_out))return -1;NetUpdate();return 0;
}
__declspec(dllexport) int32_t km_host_player_x(void) { return players[consoleplayer].mo->x; }
__declspec(dllexport) int32_t km_host_player_y(void) { return players[consoleplayer].mo->y; }
__declspec(dllexport) const char *km_host_error(void) { return error; }
__declspec(dllexport) const uint16_t *km_host_screen(void) { return screen; }
__declspec(dllexport) const uint32_t *km_host_trace(void) { return &trace[0][0]; }
__declspec(dllexport) uint32_t km_host_trace_count(void) { return trace_used; }
__declspec(dllexport) void km_host_trace_reset(void) { trace_used=0; }
__declspec(dllexport) void km_host_redraw(void) { km_doom_redraw();D_Display(); }
__declspec(dllexport) void km_host_clear_and_redraw(void) {
    memset(screen,0,sizeof(screen));km_doom_redraw();D_Display();
}
