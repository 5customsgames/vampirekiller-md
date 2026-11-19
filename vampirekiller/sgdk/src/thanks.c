#include "thanks.h"
#include "msx_text.h"
#include "gfx16.h"
#include "frontend.h"
#include "dracula_view.h"

/* Thank-you pages after the credits of the ending (research/thanks-screen.md). Text: tiles of the MSX font (vk_msx_font_row, in white on
 * transparent: PAL0 entry 14 for the headings, 13 for the names of the testers). No RAM except a few static bytes: the pages are
 * ROM strings, the glyph tiles are composed one by one on the stack. The names get two raster effects: a horizontal interrupt
 * rewrites colour 13 on every line (rainbow gradient, one ROM table indexed by the V counter) and the horizontal scroll per line
 * of plane A (sine table in ROM) makes the name rows wave. Both only live during this screen. */
#define GLYPHS 64
#define TEXT_TILE TILE_USER_INDEX /* the 1024 tiles of the credit text are no longer needed */
#define NAME_TILE (TEXT_TILE+GLYPHS)
#define PAGE_FRAMES 330
#define LAST_FRAMES 240
#define IGNORE_FRAMES 20
#define NAME_COLOR 13

static const u16 ramp[64]={0x44E,0x44E,0x46E,0x46E,0x48E,0x48E,0x4AE,0x4AE,0x4CE,0x4CE,0x4EE,0x4EE,0x4EC,0x4EC,0x4EA,0x4EA,0x4E8,0x4E8,0x4E6,0x4E6,0x4E4,0x4E4,0x4E4,0x6E4,0x6E4,0x8E4,0x8E4,0xAE4,0xAE4,0xCE4,0xCE4,0xEE4,0xEE4,0xEE4,0xEC4,0xEC4,0xEA4,0xEA4,0xE84,0xE84,0xE64,0xE64,0xE44,0xE44,0xE44,0xE46,0xE46,0xE48,0xE48,0xE4A,0xE4A,0xE4C,0xE4C,0xE4E,0xE4E,0xC4E,0xC4E,0xA4E,0xA4E,0x84E,0x84E,0x64E,0x64E,0x44E};
static const s16 wave[72]={0,0,1,1,2,2,2,3,3,3,3,4,4,4,4,4,4,4,4,4,4,4,3,3,3,3,2,2,2,1,1,0,0,0,-1,-1,-2,-2,-2,-3,-3,-3,-3,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-4,-3,-3,-3,-3,-2,-2,-2,-1,-1,0,0,0,1,1,2,2,2,3};
static const s16 zeros[32]={0};

/* '~' prefix: name line (colour cycling and wave). Empty string: blank line. */
static const char *const page1[]={"THANK YOU FOR PLAYING","","VAMPIRE KILLER MD","MSX2 TO MEGA DRIVE PORT",0};
static const char *const page2[]={"SPECIAL THANKS","","~DIDLITH","FOR MANY EVENINGS OF TESTING","","~SHINBLAZE","FOR VALIDATING THE GAME","ON REAL CONSOLE",0};
static const char *const page3[]={"ALL THE MEMBERS OF THE","~5CUSTOMS DISCORD SERVER",0};
static const char *const page4[]={"ORIGINAL GAME","VAMPIRE KILLER BY KONAMI","","16-BIT ART INSPIRED BY","CASTLEVANIA MEGA DRIVE",0};
static const char *const page5[]={"THE END",0};
static const char *const *const pages[]={page1,page2,page3,page4,page5};
#define PAGE_COUNT 5

#define thanks_frame (*vk_dracula_view_spare())
#define thanks_phase ((u8)thanks_frame)

static HINTERRUPT_CALLBACK raster(void)
{
    *(vu32*)VDP_CTRL_PORT=VDP_WRITE_CRAM_ADDR(2*NAME_COLOR);
    *(vu16*)VDP_DATA_PORT=ramp[(GET_VCOUNTER*4+thanks_phase*3)&63];
}

static u16 glyph(char c)
{
    const u16 code=c=='-'?0x30:(u16)(c-0x10);
    return code<0x20||code>=0x60?0:(u16)(code-0x20);
}
static u16 page_rows(const char *const *p){u16 n=0;while(p[n])n++;return n;}
static u16 page_of(void){u16 f=thanks_frame,n=0;while(f>=PAGE_FRAMES&&n<PAGE_COUNT-1){f-=PAGE_FRAMES;n++;}return n;}
static void draw_page(void)
{
    const char *const *p=pages[page_of()];
    const u16 n=page_rows(p),first=(u16)((28-n)/2);
    u16 row,c;
    for(row=0;row<28;row++){
        u16 cells[32];
        const char *s=row>=first&&row<first+n?p[row-first]:"";
        const bool name=*s=='~';
        u16 len,x;
        if(name)s++;
        len=(u16)strlen(s);x=(u16)((32-len)/2);
        for(c=0;c<32;c++)cells[c]=0;
        for(c=0;c<len;c++)if(s[c]!=' ')cells[x+c]=TILE_ATTR_FULL(PAL0,TRUE,FALSE,FALSE,(name?NAME_TILE:TEXT_TILE)+glyph(s[c]));
        if(!vk_gfx16&&(row==1||row==26))for(c=1;c<31;c++)cells[c]=TILE_ATTR_FULL(PAL0,TRUE,FALSE,FALSE,TEXT_TILE+glyph('-'));
        VDP_setTileMapDataRow(BG_A,cells,row,0,32,CPU);
    }
}
static void load_glyphs(void)
{
    u16 i,l;
    for(i=0;i<GLYPHS;i++){
        u32 white[8],name[8],above=0;
        for(l=0;l<8;l++){
            const u32 g=vk_msx_font_row((u8)(0x20+i),l);
            u32 m=(g|(g>>1)|(g>>2)|(g>>3))&0x11111111UL;
            u32 shadow=above>>4; /* the shadow (colour 1, black) of the row above, one pixel to the right: readable on the busy picture of the 16-bit ending */
            m*=15;above=m;shadow&=~m;
            white[l]=(m&0xEEEEEEEEUL)|(shadow&0x11111111UL);name[l]=(m&(0x11111111UL*NAME_COLOR))|(shadow&0x11111111UL);
        }
        VDP_loadTileData(white,(u16)(TEXT_TILE+i),1,CPU);
        VDP_loadTileData(name,(u16)(NAME_TILE+i),1,CPU);
    }
}
/* DMA_transfer by CPU leaves the VDP auto-increment at the step (4): restore SGDK's 2 or every later write goes astray. */
/* Every VDP access of the main loop runs with the interrupts off (SYS_disableInts): a horizontal interrupt in the middle of a two-word
 * command sends the data to the colour RAM (the raster writes a CRAM address). */
static void hscroll(VDPPlane plane,u16 line,const s16 *values,u16 len)
{
    VDP_setHorizontalScrollLine(plane,line,(s16*)values,len,CPU);VDP_setAutoInc(2);
}
static void clear_hscroll(void)
{
    u16 l;
    for(l=0;l<224;l+=32){
        hscroll(BG_A,l,zeros,32);
        hscroll(BG_B,l,zeros,32);
    }
}
void vk_thanks_begin(void)
{
    DMA_flushQueue();VDP_resetSprites();VDP_updateSprites(1,CPU);
    VDP_setEnable(FALSE);
    VDP_setScrollingMode(HSCROLL_LINE,VSCROLL_PLANE);
    clear_hscroll();
    VDP_setVerticalScroll(BG_A,0);
    PAL_setColor(0,0);PAL_setColor(1,0);PAL_setColor(14,0x0EEE);PAL_setColor(NAME_COLOR,ramp[0]);
    load_glyphs();
    thanks_frame=0;
    draw_page();
    vk_front_mode=FRONT_THANKS;
    VDP_setEnable(TRUE);
}
static void leave(void)
{
    VDP_setHInterrupt(FALSE);SYS_setHIntCallback(0);
    VDP_setScrollingMode(HSCROLL_PLANE,VSCROLL_PLANE);
    VDP_setHorizontalScroll(BG_A,0);VDP_setHorizontalScroll(BG_B,0);
}
bool vk_thanks_tick(u16 pressed)
{
    const u16 before=page_of();
    u16 row,line=0;
    const char *const *p;
    thanks_frame++;
    if(thanks_frame==1){SYS_disableInts();SYS_setHIntCallback(raster);VDP_setHIntCounter(0);VDP_setHInterrupt(TRUE);SYS_enableInts();} /* in the VBlank of the first turn */
    if((pressed&BUTTON_START)&&thanks_frame>IGNORE_FRAMES){leave();return TRUE;}
    if(thanks_frame>=PAGE_FRAMES*(PAGE_COUNT-1)+LAST_FRAMES){leave();return TRUE;}
    if(page_of()!=before){
        /* The redraw takes longer than the VBlank: the horizontal interrupt would break the VDP address of a write in progress. */
        SYS_disableInts();clear_hscroll();draw_page();SYS_enableInts();
    }
    p=pages[page_of()];
    {
        const u16 n=page_rows(p),first=(u16)((28-n)/2);
        for(row=0;row<n;row++)if(p[row][0]=='~'){
            line=(u16)((first+row)*8);
            {SYS_disableInts();hscroll(BG_A,line,wave+((line+thanks_phase)&63),8);SYS_enableInts();}
        }
    }
    return FALSE;
}
