#include <genesis.h>

__attribute__((externally_visible))
// Full-width header fields are binary data, without a C string terminator.
const ROMHeader rom_header = {
#if (MODULE_MEGAWIFI && (MEGAWIFI_IMPLEMENTATION == MEGAWIFI_IMPLEMENTATION_MW_CART))
    { 'S', 'E', 'G', 'A', ' ', 'M', 'E', 'G', 'A', 'W', 'I', 'F', 'I', ' ', ' ', ' ' },
#elif (ENABLE_BANK_SWITCH != 0)
    { 'S', 'E', 'G', 'A', ' ', 'S', 'S', 'F', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
#else
    { 'S', 'E', 'G', 'A', ' ', 'M', 'E', 'G', 'A', ' ', 'D', 'R', 'I', 'V', 'E', ' ' },
#endif
    { '(', 'C', ')', '5', 'C', 'u', 's', 't', 'o', 'm', 's', ' ', '2', '0', '2', '6' },
    { 'C', 'a', 's', 't', 'l', 'e', 'v', 'a', 'n', 'i', 'a', '-', 'M', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    { 'C', 'a', 's', 't', 'l', 'e', 'v', 'a', 'n', 'i', 'a', '-', 'M', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    { 'G', 'M', ' ', '5', 'C', 'U', 'N', 'I', 'K', '-', '0', '1', ' ', ' ' },
    0x000,
    { 'J', 'D', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    0x00000000,
#if (ENABLE_BANK_SWITCH != 0)
    0x003FFFFF,
#else
    0x000FFFFF,
#endif
    0xE0FF0000,
    0xE0FFFFFF,
    { 'R', 'A' },
    0xF820,
    0x00200000,
    0x0020FFFF,
    { ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' },
    "PORT BY 5CUSTOMS STUDIO",
    { 'J', 'U', 'E', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ' }
};
