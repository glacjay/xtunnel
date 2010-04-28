#ifndef INCLUDE__OPTIONS_H
#define INCLUDE__OPTIONS_H


typedef struct options_s {
    char *prog_name;

#define MODE_SERVER 0
#define MODE_CLIENT 1
    int mode;
    char *snat_name; // valid when MODE_CLIENT only
} options_t;


void options_init(options_t *o, int argc, char **argv);


#endif
