#ifndef INCLUDE__MAIN_H
#define INCLUDE__MAIN_H

#include "options.h"


typedef struct context_s {
    options_t o;

    char client_connected;
} context_t;

extern context_t c;


#endif
