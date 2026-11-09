#include "../third_party/gpu-screen-recorder/plugin/plugin.h"
#include <stddef.h>
#include <stdio.h>
int main(void) {
    printf("api %d %d\n", GSR_PLUGIN_INTERFACE_MAJOR_VERSION, GSR_PLUGIN_INTERFACE_MINOR_VERSION);
    printf("draw %zu %zu %zu %zu\n", sizeof(gsr_plugin_draw_params), _Alignof(gsr_plugin_draw_params),
           offsetof(gsr_plugin_draw_params, width), offsetof(gsr_plugin_draw_params, height));
    printf("init %zu %zu %zu %zu %zu %zu %zu\n", sizeof(gsr_plugin_init_params), _Alignof(gsr_plugin_init_params),
           offsetof(gsr_plugin_init_params, width), offsetof(gsr_plugin_init_params, height), offsetof(gsr_plugin_init_params, fps),
           offsetof(gsr_plugin_init_params, color_depth), offsetof(gsr_plugin_init_params, graphics_api));
    printf("return %zu %zu %zu %zu %zu %zu %zu %zu\n", sizeof(gsr_plugin_init_return), _Alignof(gsr_plugin_init_return),
           offsetof(gsr_plugin_init_return, name), offsetof(gsr_plugin_init_return, version), offsetof(gsr_plugin_init_return, userdata),
           offsetof(gsr_plugin_init_return, draw), offsetof(gsr_plugin_init_return, is_damaged), offsetof(gsr_plugin_init_return, clear_damage));
    _Static_assert(sizeof(gsr_plugin_graphics_api) == sizeof(int), "graphics_api layout");
    _Static_assert(sizeof(gsr_plugin_color_depth) == sizeof(int), "color_depth layout");
    printf("primitives %zu %zu %zu %zu\n", sizeof(unsigned int), sizeof(int), sizeof(bool), sizeof(((gsr_plugin_init_return*)0)->draw));
    return 0;
}
