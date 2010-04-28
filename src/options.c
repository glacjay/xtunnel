#include "main.h"
#include "options.h"
#include "utils.h"


void options_init(options_t *o, int argc, char **argv)
{
    o->prog_name = argv[0];
    argc--;
    argv++;

    if (argc == 1 && *argv[0] != '-') {
        o->mode = MODE_CLIENT;
        o->snat_name = argv[0];
    }
}
