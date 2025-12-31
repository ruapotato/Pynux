# Pynux Graphics Library - Text Rendering
#
# 8x8 bitmap font text rendering for bare-metal ARM.
# Supports multiple font sizes and custom fonts.

from lib.gfx.framebuffer import fb_set_pixel, fb_is_initialized

# ============================================================================
# Default 8x8 Bitmap Font
# ============================================================================
# Each character is 8 bytes (8 rows of 8 bits each)
# Bit 0 is leftmost pixel, bit 7 is rightmost
# Characters 32-126 (printable ASCII)

# Font data for ASCII 32-126 (95 characters * 8 bytes = 760 bytes)
_font_8x8: Array[760, uint8]
_font_initialized: bool = False

# Current font pointer and settings
_font_data: Ptr[uint8] = cast[Ptr[uint8]](0)
_font_width: int32 = 8
_font_height: int32 = 8
_font_first_char: int32 = 32
_font_last_char: int32 = 126
_font_size: int32 = 1  # Size multiplier

def _init_default_font():
    """Initialize the default 8x8 bitmap font."""
    global _font_initialized, _font_data

    if _font_initialized:
        return

    # Space (32)
    _font_8x8[0] = 0x00
    _font_8x8[1] = 0x00
    _font_8x8[2] = 0x00
    _font_8x8[3] = 0x00
    _font_8x8[4] = 0x00
    _font_8x8[5] = 0x00
    _font_8x8[6] = 0x00
    _font_8x8[7] = 0x00

    # ! (33)
    _font_8x8[8] = 0x18
    _font_8x8[9] = 0x18
    _font_8x8[10] = 0x18
    _font_8x8[11] = 0x18
    _font_8x8[12] = 0x18
    _font_8x8[13] = 0x00
    _font_8x8[14] = 0x18
    _font_8x8[15] = 0x00

    # " (34)
    _font_8x8[16] = 0x6C
    _font_8x8[17] = 0x6C
    _font_8x8[18] = 0x24
    _font_8x8[19] = 0x00
    _font_8x8[20] = 0x00
    _font_8x8[21] = 0x00
    _font_8x8[22] = 0x00
    _font_8x8[23] = 0x00

    # # (35)
    _font_8x8[24] = 0x6C
    _font_8x8[25] = 0x6C
    _font_8x8[26] = 0xFE
    _font_8x8[27] = 0x6C
    _font_8x8[28] = 0xFE
    _font_8x8[29] = 0x6C
    _font_8x8[30] = 0x6C
    _font_8x8[31] = 0x00

    # $ (36)
    _font_8x8[32] = 0x18
    _font_8x8[33] = 0x3E
    _font_8x8[34] = 0x60
    _font_8x8[35] = 0x3C
    _font_8x8[36] = 0x06
    _font_8x8[37] = 0x7C
    _font_8x8[38] = 0x18
    _font_8x8[39] = 0x00

    # % (37)
    _font_8x8[40] = 0x00
    _font_8x8[41] = 0x66
    _font_8x8[42] = 0xAC
    _font_8x8[43] = 0xD8
    _font_8x8[44] = 0x36
    _font_8x8[45] = 0x6A
    _font_8x8[46] = 0xCC
    _font_8x8[47] = 0x00

    # & (38)
    _font_8x8[48] = 0x38
    _font_8x8[49] = 0x6C
    _font_8x8[50] = 0x68
    _font_8x8[51] = 0x76
    _font_8x8[52] = 0xDC
    _font_8x8[53] = 0xCE
    _font_8x8[54] = 0x7B
    _font_8x8[55] = 0x00

    # ' (39)
    _font_8x8[56] = 0x18
    _font_8x8[57] = 0x18
    _font_8x8[58] = 0x30
    _font_8x8[59] = 0x00
    _font_8x8[60] = 0x00
    _font_8x8[61] = 0x00
    _font_8x8[62] = 0x00
    _font_8x8[63] = 0x00

    # ( (40)
    _font_8x8[64] = 0x0C
    _font_8x8[65] = 0x18
    _font_8x8[66] = 0x30
    _font_8x8[67] = 0x30
    _font_8x8[68] = 0x30
    _font_8x8[69] = 0x18
    _font_8x8[70] = 0x0C
    _font_8x8[71] = 0x00

    # ) (41)
    _font_8x8[72] = 0x30
    _font_8x8[73] = 0x18
    _font_8x8[74] = 0x0C
    _font_8x8[75] = 0x0C
    _font_8x8[76] = 0x0C
    _font_8x8[77] = 0x18
    _font_8x8[78] = 0x30
    _font_8x8[79] = 0x00

    # * (42)
    _font_8x8[80] = 0x00
    _font_8x8[81] = 0x66
    _font_8x8[82] = 0x3C
    _font_8x8[83] = 0xFF
    _font_8x8[84] = 0x3C
    _font_8x8[85] = 0x66
    _font_8x8[86] = 0x00
    _font_8x8[87] = 0x00

    # + (43)
    _font_8x8[88] = 0x00
    _font_8x8[89] = 0x18
    _font_8x8[90] = 0x18
    _font_8x8[91] = 0x7E
    _font_8x8[92] = 0x18
    _font_8x8[93] = 0x18
    _font_8x8[94] = 0x00
    _font_8x8[95] = 0x00

    # , (44)
    _font_8x8[96] = 0x00
    _font_8x8[97] = 0x00
    _font_8x8[98] = 0x00
    _font_8x8[99] = 0x00
    _font_8x8[100] = 0x00
    _font_8x8[101] = 0x18
    _font_8x8[102] = 0x18
    _font_8x8[103] = 0x30

    # - (45)
    _font_8x8[104] = 0x00
    _font_8x8[105] = 0x00
    _font_8x8[106] = 0x00
    _font_8x8[107] = 0x7E
    _font_8x8[108] = 0x00
    _font_8x8[109] = 0x00
    _font_8x8[110] = 0x00
    _font_8x8[111] = 0x00

    # . (46)
    _font_8x8[112] = 0x00
    _font_8x8[113] = 0x00
    _font_8x8[114] = 0x00
    _font_8x8[115] = 0x00
    _font_8x8[116] = 0x00
    _font_8x8[117] = 0x18
    _font_8x8[118] = 0x18
    _font_8x8[119] = 0x00

    # / (47)
    _font_8x8[120] = 0x06
    _font_8x8[121] = 0x0C
    _font_8x8[122] = 0x18
    _font_8x8[123] = 0x30
    _font_8x8[124] = 0x60
    _font_8x8[125] = 0xC0
    _font_8x8[126] = 0x80
    _font_8x8[127] = 0x00

    # 0-9 (48-57)
    # 0
    _font_8x8[128] = 0x3C
    _font_8x8[129] = 0x66
    _font_8x8[130] = 0x6E
    _font_8x8[131] = 0x7E
    _font_8x8[132] = 0x76
    _font_8x8[133] = 0x66
    _font_8x8[134] = 0x3C
    _font_8x8[135] = 0x00

    # 1
    _font_8x8[136] = 0x18
    _font_8x8[137] = 0x38
    _font_8x8[138] = 0x18
    _font_8x8[139] = 0x18
    _font_8x8[140] = 0x18
    _font_8x8[141] = 0x18
    _font_8x8[142] = 0x7E
    _font_8x8[143] = 0x00

    # 2
    _font_8x8[144] = 0x3C
    _font_8x8[145] = 0x66
    _font_8x8[146] = 0x06
    _font_8x8[147] = 0x0C
    _font_8x8[148] = 0x18
    _font_8x8[149] = 0x30
    _font_8x8[150] = 0x7E
    _font_8x8[151] = 0x00

    # 3
    _font_8x8[152] = 0x3C
    _font_8x8[153] = 0x66
    _font_8x8[154] = 0x06
    _font_8x8[155] = 0x1C
    _font_8x8[156] = 0x06
    _font_8x8[157] = 0x66
    _font_8x8[158] = 0x3C
    _font_8x8[159] = 0x00

    # 4
    _font_8x8[160] = 0x0C
    _font_8x8[161] = 0x1C
    _font_8x8[162] = 0x3C
    _font_8x8[163] = 0x6C
    _font_8x8[164] = 0x7E
    _font_8x8[165] = 0x0C
    _font_8x8[166] = 0x0C
    _font_8x8[167] = 0x00

    # 5
    _font_8x8[168] = 0x7E
    _font_8x8[169] = 0x60
    _font_8x8[170] = 0x7C
    _font_8x8[171] = 0x06
    _font_8x8[172] = 0x06
    _font_8x8[173] = 0x66
    _font_8x8[174] = 0x3C
    _font_8x8[175] = 0x00

    # 6
    _font_8x8[176] = 0x1C
    _font_8x8[177] = 0x30
    _font_8x8[178] = 0x60
    _font_8x8[179] = 0x7C
    _font_8x8[180] = 0x66
    _font_8x8[181] = 0x66
    _font_8x8[182] = 0x3C
    _font_8x8[183] = 0x00

    # 7
    _font_8x8[184] = 0x7E
    _font_8x8[185] = 0x06
    _font_8x8[186] = 0x0C
    _font_8x8[187] = 0x18
    _font_8x8[188] = 0x30
    _font_8x8[189] = 0x30
    _font_8x8[190] = 0x30
    _font_8x8[191] = 0x00

    # 8
    _font_8x8[192] = 0x3C
    _font_8x8[193] = 0x66
    _font_8x8[194] = 0x66
    _font_8x8[195] = 0x3C
    _font_8x8[196] = 0x66
    _font_8x8[197] = 0x66
    _font_8x8[198] = 0x3C
    _font_8x8[199] = 0x00

    # 9
    _font_8x8[200] = 0x3C
    _font_8x8[201] = 0x66
    _font_8x8[202] = 0x66
    _font_8x8[203] = 0x3E
    _font_8x8[204] = 0x06
    _font_8x8[205] = 0x0C
    _font_8x8[206] = 0x38
    _font_8x8[207] = 0x00

    # : (58)
    _font_8x8[208] = 0x00
    _font_8x8[209] = 0x00
    _font_8x8[210] = 0x18
    _font_8x8[211] = 0x18
    _font_8x8[212] = 0x00
    _font_8x8[213] = 0x18
    _font_8x8[214] = 0x18
    _font_8x8[215] = 0x00

    # ; (59)
    _font_8x8[216] = 0x00
    _font_8x8[217] = 0x00
    _font_8x8[218] = 0x18
    _font_8x8[219] = 0x18
    _font_8x8[220] = 0x00
    _font_8x8[221] = 0x18
    _font_8x8[222] = 0x18
    _font_8x8[223] = 0x30

    # < (60)
    _font_8x8[224] = 0x0C
    _font_8x8[225] = 0x18
    _font_8x8[226] = 0x30
    _font_8x8[227] = 0x60
    _font_8x8[228] = 0x30
    _font_8x8[229] = 0x18
    _font_8x8[230] = 0x0C
    _font_8x8[231] = 0x00

    # = (61)
    _font_8x8[232] = 0x00
    _font_8x8[233] = 0x00
    _font_8x8[234] = 0x7E
    _font_8x8[235] = 0x00
    _font_8x8[236] = 0x7E
    _font_8x8[237] = 0x00
    _font_8x8[238] = 0x00
    _font_8x8[239] = 0x00

    # > (62)
    _font_8x8[240] = 0x30
    _font_8x8[241] = 0x18
    _font_8x8[242] = 0x0C
    _font_8x8[243] = 0x06
    _font_8x8[244] = 0x0C
    _font_8x8[245] = 0x18
    _font_8x8[246] = 0x30
    _font_8x8[247] = 0x00

    # ? (63)
    _font_8x8[248] = 0x3C
    _font_8x8[249] = 0x66
    _font_8x8[250] = 0x06
    _font_8x8[251] = 0x0C
    _font_8x8[252] = 0x18
    _font_8x8[253] = 0x00
    _font_8x8[254] = 0x18
    _font_8x8[255] = 0x00

    # @ (64)
    _font_8x8[256] = 0x3C
    _font_8x8[257] = 0x66
    _font_8x8[258] = 0x6E
    _font_8x8[259] = 0x6A
    _font_8x8[260] = 0x6E
    _font_8x8[261] = 0x60
    _font_8x8[262] = 0x3C
    _font_8x8[263] = 0x00

    # A-Z (65-90)
    # A
    _font_8x8[264] = 0x18
    _font_8x8[265] = 0x3C
    _font_8x8[266] = 0x66
    _font_8x8[267] = 0x66
    _font_8x8[268] = 0x7E
    _font_8x8[269] = 0x66
    _font_8x8[270] = 0x66
    _font_8x8[271] = 0x00

    # B
    _font_8x8[272] = 0x7C
    _font_8x8[273] = 0x66
    _font_8x8[274] = 0x66
    _font_8x8[275] = 0x7C
    _font_8x8[276] = 0x66
    _font_8x8[277] = 0x66
    _font_8x8[278] = 0x7C
    _font_8x8[279] = 0x00

    # C
    _font_8x8[280] = 0x3C
    _font_8x8[281] = 0x66
    _font_8x8[282] = 0x60
    _font_8x8[283] = 0x60
    _font_8x8[284] = 0x60
    _font_8x8[285] = 0x66
    _font_8x8[286] = 0x3C
    _font_8x8[287] = 0x00

    # D
    _font_8x8[288] = 0x78
    _font_8x8[289] = 0x6C
    _font_8x8[290] = 0x66
    _font_8x8[291] = 0x66
    _font_8x8[292] = 0x66
    _font_8x8[293] = 0x6C
    _font_8x8[294] = 0x78
    _font_8x8[295] = 0x00

    # E
    _font_8x8[296] = 0x7E
    _font_8x8[297] = 0x60
    _font_8x8[298] = 0x60
    _font_8x8[299] = 0x7C
    _font_8x8[300] = 0x60
    _font_8x8[301] = 0x60
    _font_8x8[302] = 0x7E
    _font_8x8[303] = 0x00

    # F
    _font_8x8[304] = 0x7E
    _font_8x8[305] = 0x60
    _font_8x8[306] = 0x60
    _font_8x8[307] = 0x7C
    _font_8x8[308] = 0x60
    _font_8x8[309] = 0x60
    _font_8x8[310] = 0x60
    _font_8x8[311] = 0x00

    # G
    _font_8x8[312] = 0x3C
    _font_8x8[313] = 0x66
    _font_8x8[314] = 0x60
    _font_8x8[315] = 0x6E
    _font_8x8[316] = 0x66
    _font_8x8[317] = 0x66
    _font_8x8[318] = 0x3E
    _font_8x8[319] = 0x00

    # H
    _font_8x8[320] = 0x66
    _font_8x8[321] = 0x66
    _font_8x8[322] = 0x66
    _font_8x8[323] = 0x7E
    _font_8x8[324] = 0x66
    _font_8x8[325] = 0x66
    _font_8x8[326] = 0x66
    _font_8x8[327] = 0x00

    # I
    _font_8x8[328] = 0x7E
    _font_8x8[329] = 0x18
    _font_8x8[330] = 0x18
    _font_8x8[331] = 0x18
    _font_8x8[332] = 0x18
    _font_8x8[333] = 0x18
    _font_8x8[334] = 0x7E
    _font_8x8[335] = 0x00

    # J
    _font_8x8[336] = 0x3E
    _font_8x8[337] = 0x0C
    _font_8x8[338] = 0x0C
    _font_8x8[339] = 0x0C
    _font_8x8[340] = 0x0C
    _font_8x8[341] = 0x6C
    _font_8x8[342] = 0x38
    _font_8x8[343] = 0x00

    # K
    _font_8x8[344] = 0x66
    _font_8x8[345] = 0x6C
    _font_8x8[346] = 0x78
    _font_8x8[347] = 0x70
    _font_8x8[348] = 0x78
    _font_8x8[349] = 0x6C
    _font_8x8[350] = 0x66
    _font_8x8[351] = 0x00

    # L
    _font_8x8[352] = 0x60
    _font_8x8[353] = 0x60
    _font_8x8[354] = 0x60
    _font_8x8[355] = 0x60
    _font_8x8[356] = 0x60
    _font_8x8[357] = 0x60
    _font_8x8[358] = 0x7E
    _font_8x8[359] = 0x00

    # M
    _font_8x8[360] = 0xC6
    _font_8x8[361] = 0xEE
    _font_8x8[362] = 0xFE
    _font_8x8[363] = 0xD6
    _font_8x8[364] = 0xC6
    _font_8x8[365] = 0xC6
    _font_8x8[366] = 0xC6
    _font_8x8[367] = 0x00

    # N
    _font_8x8[368] = 0x66
    _font_8x8[369] = 0x66
    _font_8x8[370] = 0x76
    _font_8x8[371] = 0x7E
    _font_8x8[372] = 0x6E
    _font_8x8[373] = 0x66
    _font_8x8[374] = 0x66
    _font_8x8[375] = 0x00

    # O
    _font_8x8[376] = 0x3C
    _font_8x8[377] = 0x66
    _font_8x8[378] = 0x66
    _font_8x8[379] = 0x66
    _font_8x8[380] = 0x66
    _font_8x8[381] = 0x66
    _font_8x8[382] = 0x3C
    _font_8x8[383] = 0x00

    # P
    _font_8x8[384] = 0x7C
    _font_8x8[385] = 0x66
    _font_8x8[386] = 0x66
    _font_8x8[387] = 0x7C
    _font_8x8[388] = 0x60
    _font_8x8[389] = 0x60
    _font_8x8[390] = 0x60
    _font_8x8[391] = 0x00

    # Q
    _font_8x8[392] = 0x3C
    _font_8x8[393] = 0x66
    _font_8x8[394] = 0x66
    _font_8x8[395] = 0x66
    _font_8x8[396] = 0x6A
    _font_8x8[397] = 0x6C
    _font_8x8[398] = 0x36
    _font_8x8[399] = 0x00

    # R
    _font_8x8[400] = 0x7C
    _font_8x8[401] = 0x66
    _font_8x8[402] = 0x66
    _font_8x8[403] = 0x7C
    _font_8x8[404] = 0x6C
    _font_8x8[405] = 0x66
    _font_8x8[406] = 0x66
    _font_8x8[407] = 0x00

    # S
    _font_8x8[408] = 0x3C
    _font_8x8[409] = 0x66
    _font_8x8[410] = 0x60
    _font_8x8[411] = 0x3C
    _font_8x8[412] = 0x06
    _font_8x8[413] = 0x66
    _font_8x8[414] = 0x3C
    _font_8x8[415] = 0x00

    # T
    _font_8x8[416] = 0x7E
    _font_8x8[417] = 0x18
    _font_8x8[418] = 0x18
    _font_8x8[419] = 0x18
    _font_8x8[420] = 0x18
    _font_8x8[421] = 0x18
    _font_8x8[422] = 0x18
    _font_8x8[423] = 0x00

    # U
    _font_8x8[424] = 0x66
    _font_8x8[425] = 0x66
    _font_8x8[426] = 0x66
    _font_8x8[427] = 0x66
    _font_8x8[428] = 0x66
    _font_8x8[429] = 0x66
    _font_8x8[430] = 0x3C
    _font_8x8[431] = 0x00

    # V
    _font_8x8[432] = 0x66
    _font_8x8[433] = 0x66
    _font_8x8[434] = 0x66
    _font_8x8[435] = 0x66
    _font_8x8[436] = 0x66
    _font_8x8[437] = 0x3C
    _font_8x8[438] = 0x18
    _font_8x8[439] = 0x00

    # W
    _font_8x8[440] = 0xC6
    _font_8x8[441] = 0xC6
    _font_8x8[442] = 0xC6
    _font_8x8[443] = 0xD6
    _font_8x8[444] = 0xFE
    _font_8x8[445] = 0xEE
    _font_8x8[446] = 0xC6
    _font_8x8[447] = 0x00

    # X
    _font_8x8[448] = 0x66
    _font_8x8[449] = 0x66
    _font_8x8[450] = 0x3C
    _font_8x8[451] = 0x18
    _font_8x8[452] = 0x3C
    _font_8x8[453] = 0x66
    _font_8x8[454] = 0x66
    _font_8x8[455] = 0x00

    # Y
    _font_8x8[456] = 0x66
    _font_8x8[457] = 0x66
    _font_8x8[458] = 0x66
    _font_8x8[459] = 0x3C
    _font_8x8[460] = 0x18
    _font_8x8[461] = 0x18
    _font_8x8[462] = 0x18
    _font_8x8[463] = 0x00

    # Z
    _font_8x8[464] = 0x7E
    _font_8x8[465] = 0x06
    _font_8x8[466] = 0x0C
    _font_8x8[467] = 0x18
    _font_8x8[468] = 0x30
    _font_8x8[469] = 0x60
    _font_8x8[470] = 0x7E
    _font_8x8[471] = 0x00

    # [ (91)
    _font_8x8[472] = 0x3C
    _font_8x8[473] = 0x30
    _font_8x8[474] = 0x30
    _font_8x8[475] = 0x30
    _font_8x8[476] = 0x30
    _font_8x8[477] = 0x30
    _font_8x8[478] = 0x3C
    _font_8x8[479] = 0x00

    # \ (92)
    _font_8x8[480] = 0xC0
    _font_8x8[481] = 0x60
    _font_8x8[482] = 0x30
    _font_8x8[483] = 0x18
    _font_8x8[484] = 0x0C
    _font_8x8[485] = 0x06
    _font_8x8[486] = 0x03
    _font_8x8[487] = 0x00

    # ] (93)
    _font_8x8[488] = 0x3C
    _font_8x8[489] = 0x0C
    _font_8x8[490] = 0x0C
    _font_8x8[491] = 0x0C
    _font_8x8[492] = 0x0C
    _font_8x8[493] = 0x0C
    _font_8x8[494] = 0x3C
    _font_8x8[495] = 0x00

    # ^ (94)
    _font_8x8[496] = 0x18
    _font_8x8[497] = 0x3C
    _font_8x8[498] = 0x66
    _font_8x8[499] = 0x00
    _font_8x8[500] = 0x00
    _font_8x8[501] = 0x00
    _font_8x8[502] = 0x00
    _font_8x8[503] = 0x00

    # _ (95)
    _font_8x8[504] = 0x00
    _font_8x8[505] = 0x00
    _font_8x8[506] = 0x00
    _font_8x8[507] = 0x00
    _font_8x8[508] = 0x00
    _font_8x8[509] = 0x00
    _font_8x8[510] = 0x00
    _font_8x8[511] = 0xFF

    # ` (96)
    _font_8x8[512] = 0x30
    _font_8x8[513] = 0x18
    _font_8x8[514] = 0x0C
    _font_8x8[515] = 0x00
    _font_8x8[516] = 0x00
    _font_8x8[517] = 0x00
    _font_8x8[518] = 0x00
    _font_8x8[519] = 0x00

    # a-z (97-122)
    # a
    _font_8x8[520] = 0x00
    _font_8x8[521] = 0x00
    _font_8x8[522] = 0x3C
    _font_8x8[523] = 0x06
    _font_8x8[524] = 0x3E
    _font_8x8[525] = 0x66
    _font_8x8[526] = 0x3E
    _font_8x8[527] = 0x00

    # b
    _font_8x8[528] = 0x60
    _font_8x8[529] = 0x60
    _font_8x8[530] = 0x7C
    _font_8x8[531] = 0x66
    _font_8x8[532] = 0x66
    _font_8x8[533] = 0x66
    _font_8x8[534] = 0x7C
    _font_8x8[535] = 0x00

    # c
    _font_8x8[536] = 0x00
    _font_8x8[537] = 0x00
    _font_8x8[538] = 0x3C
    _font_8x8[539] = 0x66
    _font_8x8[540] = 0x60
    _font_8x8[541] = 0x66
    _font_8x8[542] = 0x3C
    _font_8x8[543] = 0x00

    # d
    _font_8x8[544] = 0x06
    _font_8x8[545] = 0x06
    _font_8x8[546] = 0x3E
    _font_8x8[547] = 0x66
    _font_8x8[548] = 0x66
    _font_8x8[549] = 0x66
    _font_8x8[550] = 0x3E
    _font_8x8[551] = 0x00

    # e
    _font_8x8[552] = 0x00
    _font_8x8[553] = 0x00
    _font_8x8[554] = 0x3C
    _font_8x8[555] = 0x66
    _font_8x8[556] = 0x7E
    _font_8x8[557] = 0x60
    _font_8x8[558] = 0x3C
    _font_8x8[559] = 0x00

    # f
    _font_8x8[560] = 0x1C
    _font_8x8[561] = 0x30
    _font_8x8[562] = 0x30
    _font_8x8[563] = 0x7C
    _font_8x8[564] = 0x30
    _font_8x8[565] = 0x30
    _font_8x8[566] = 0x30
    _font_8x8[567] = 0x00

    # g
    _font_8x8[568] = 0x00
    _font_8x8[569] = 0x00
    _font_8x8[570] = 0x3E
    _font_8x8[571] = 0x66
    _font_8x8[572] = 0x66
    _font_8x8[573] = 0x3E
    _font_8x8[574] = 0x06
    _font_8x8[575] = 0x3C

    # h
    _font_8x8[576] = 0x60
    _font_8x8[577] = 0x60
    _font_8x8[578] = 0x7C
    _font_8x8[579] = 0x66
    _font_8x8[580] = 0x66
    _font_8x8[581] = 0x66
    _font_8x8[582] = 0x66
    _font_8x8[583] = 0x00

    # i
    _font_8x8[584] = 0x18
    _font_8x8[585] = 0x00
    _font_8x8[586] = 0x38
    _font_8x8[587] = 0x18
    _font_8x8[588] = 0x18
    _font_8x8[589] = 0x18
    _font_8x8[590] = 0x3C
    _font_8x8[591] = 0x00

    # j
    _font_8x8[592] = 0x0C
    _font_8x8[593] = 0x00
    _font_8x8[594] = 0x1C
    _font_8x8[595] = 0x0C
    _font_8x8[596] = 0x0C
    _font_8x8[597] = 0x0C
    _font_8x8[598] = 0x6C
    _font_8x8[599] = 0x38

    # k
    _font_8x8[600] = 0x60
    _font_8x8[601] = 0x60
    _font_8x8[602] = 0x66
    _font_8x8[603] = 0x6C
    _font_8x8[604] = 0x78
    _font_8x8[605] = 0x6C
    _font_8x8[606] = 0x66
    _font_8x8[607] = 0x00

    # l
    _font_8x8[608] = 0x38
    _font_8x8[609] = 0x18
    _font_8x8[610] = 0x18
    _font_8x8[611] = 0x18
    _font_8x8[612] = 0x18
    _font_8x8[613] = 0x18
    _font_8x8[614] = 0x3C
    _font_8x8[615] = 0x00

    # m
    _font_8x8[616] = 0x00
    _font_8x8[617] = 0x00
    _font_8x8[618] = 0xEC
    _font_8x8[619] = 0xFE
    _font_8x8[620] = 0xD6
    _font_8x8[621] = 0xC6
    _font_8x8[622] = 0xC6
    _font_8x8[623] = 0x00

    # n
    _font_8x8[624] = 0x00
    _font_8x8[625] = 0x00
    _font_8x8[626] = 0x7C
    _font_8x8[627] = 0x66
    _font_8x8[628] = 0x66
    _font_8x8[629] = 0x66
    _font_8x8[630] = 0x66
    _font_8x8[631] = 0x00

    # o
    _font_8x8[632] = 0x00
    _font_8x8[633] = 0x00
    _font_8x8[634] = 0x3C
    _font_8x8[635] = 0x66
    _font_8x8[636] = 0x66
    _font_8x8[637] = 0x66
    _font_8x8[638] = 0x3C
    _font_8x8[639] = 0x00

    # p
    _font_8x8[640] = 0x00
    _font_8x8[641] = 0x00
    _font_8x8[642] = 0x7C
    _font_8x8[643] = 0x66
    _font_8x8[644] = 0x66
    _font_8x8[645] = 0x7C
    _font_8x8[646] = 0x60
    _font_8x8[647] = 0x60

    # q
    _font_8x8[648] = 0x00
    _font_8x8[649] = 0x00
    _font_8x8[650] = 0x3E
    _font_8x8[651] = 0x66
    _font_8x8[652] = 0x66
    _font_8x8[653] = 0x3E
    _font_8x8[654] = 0x06
    _font_8x8[655] = 0x06

    # r
    _font_8x8[656] = 0x00
    _font_8x8[657] = 0x00
    _font_8x8[658] = 0x7C
    _font_8x8[659] = 0x66
    _font_8x8[660] = 0x60
    _font_8x8[661] = 0x60
    _font_8x8[662] = 0x60
    _font_8x8[663] = 0x00

    # s
    _font_8x8[664] = 0x00
    _font_8x8[665] = 0x00
    _font_8x8[666] = 0x3E
    _font_8x8[667] = 0x60
    _font_8x8[668] = 0x3C
    _font_8x8[669] = 0x06
    _font_8x8[670] = 0x7C
    _font_8x8[671] = 0x00

    # t
    _font_8x8[672] = 0x30
    _font_8x8[673] = 0x30
    _font_8x8[674] = 0x7C
    _font_8x8[675] = 0x30
    _font_8x8[676] = 0x30
    _font_8x8[677] = 0x30
    _font_8x8[678] = 0x1C
    _font_8x8[679] = 0x00

    # u
    _font_8x8[680] = 0x00
    _font_8x8[681] = 0x00
    _font_8x8[682] = 0x66
    _font_8x8[683] = 0x66
    _font_8x8[684] = 0x66
    _font_8x8[685] = 0x66
    _font_8x8[686] = 0x3E
    _font_8x8[687] = 0x00

    # v
    _font_8x8[688] = 0x00
    _font_8x8[689] = 0x00
    _font_8x8[690] = 0x66
    _font_8x8[691] = 0x66
    _font_8x8[692] = 0x66
    _font_8x8[693] = 0x3C
    _font_8x8[694] = 0x18
    _font_8x8[695] = 0x00

    # w
    _font_8x8[696] = 0x00
    _font_8x8[697] = 0x00
    _font_8x8[698] = 0xC6
    _font_8x8[699] = 0xC6
    _font_8x8[700] = 0xD6
    _font_8x8[701] = 0xFE
    _font_8x8[702] = 0x6C
    _font_8x8[703] = 0x00

    # x
    _font_8x8[704] = 0x00
    _font_8x8[705] = 0x00
    _font_8x8[706] = 0x66
    _font_8x8[707] = 0x3C
    _font_8x8[708] = 0x18
    _font_8x8[709] = 0x3C
    _font_8x8[710] = 0x66
    _font_8x8[711] = 0x00

    # y
    _font_8x8[712] = 0x00
    _font_8x8[713] = 0x00
    _font_8x8[714] = 0x66
    _font_8x8[715] = 0x66
    _font_8x8[716] = 0x66
    _font_8x8[717] = 0x3E
    _font_8x8[718] = 0x06
    _font_8x8[719] = 0x3C

    # z
    _font_8x8[720] = 0x00
    _font_8x8[721] = 0x00
    _font_8x8[722] = 0x7E
    _font_8x8[723] = 0x0C
    _font_8x8[724] = 0x18
    _font_8x8[725] = 0x30
    _font_8x8[726] = 0x7E
    _font_8x8[727] = 0x00

    # { (123)
    _font_8x8[728] = 0x0E
    _font_8x8[729] = 0x18
    _font_8x8[730] = 0x18
    _font_8x8[731] = 0x70
    _font_8x8[732] = 0x18
    _font_8x8[733] = 0x18
    _font_8x8[734] = 0x0E
    _font_8x8[735] = 0x00

    # | (124)
    _font_8x8[736] = 0x18
    _font_8x8[737] = 0x18
    _font_8x8[738] = 0x18
    _font_8x8[739] = 0x18
    _font_8x8[740] = 0x18
    _font_8x8[741] = 0x18
    _font_8x8[742] = 0x18
    _font_8x8[743] = 0x00

    # } (125)
    _font_8x8[744] = 0x70
    _font_8x8[745] = 0x18
    _font_8x8[746] = 0x18
    _font_8x8[747] = 0x0E
    _font_8x8[748] = 0x18
    _font_8x8[749] = 0x18
    _font_8x8[750] = 0x70
    _font_8x8[751] = 0x00

    # ~ (126)
    _font_8x8[752] = 0x00
    _font_8x8[753] = 0x00
    _font_8x8[754] = 0x60
    _font_8x8[755] = 0x92
    _font_8x8[756] = 0x0C
    _font_8x8[757] = 0x00
    _font_8x8[758] = 0x00
    _font_8x8[759] = 0x00

    _font_data = &_font_8x8[0]
    _font_initialized = True

# ============================================================================
# Text Initialization and Configuration
# ============================================================================

def text_init():
    """Initialize text rendering system with default font."""
    global _font_width, _font_height, _font_first_char, _font_last_char, _font_size

    _init_default_font()

    _font_width = 8
    _font_height = 8
    _font_first_char = 32
    _font_last_char = 126
    _font_size = 1

def text_set_font(font_data: Ptr[uint8], width: int32, height: int32,
                  first_char: int32, last_char: int32):
    """Set custom font data.

    Font is stored as sequential bytes per character, each byte being
    one row of pixels (bit 0 = leftmost).

    Args:
        font_data: Pointer to font bitmap data
        width: Character width in pixels
        height: Character height in pixels
        first_char: ASCII code of first character in font
        last_char: ASCII code of last character in font
    """
    global _font_data, _font_width, _font_height, _font_first_char, _font_last_char

    _font_data = font_data
    _font_width = width
    _font_height = height
    _font_first_char = first_char
    _font_last_char = last_char

def text_set_size(size: int32):
    """Set font size multiplier.

    Args:
        size: Size multiplier (1 = normal, 2 = double, etc.)
    """
    global _font_size

    if size < 1:
        size = 1
    if size > 8:
        size = 8

    _font_size = size

def text_get_size() -> int32:
    """Get current font size multiplier.

    Returns:
        Current size multiplier
    """
    return _font_size

def text_get_width() -> int32:
    """Get current font character width.

    Returns:
        Character width in pixels (before scaling)
    """
    return _font_width

def text_get_height() -> int32:
    """Get current font character height.

    Returns:
        Character height in pixels (before scaling)
    """
    return _font_height

# ============================================================================
# Text Drawing Functions
# ============================================================================

def text_draw_char(x: int32, y: int32, ch: char, color: uint32) -> int32:
    """Draw a single character.

    Args:
        x, y: Position (top-left)
        ch: Character to draw
        color: Text color

    Returns:
        Width of drawn character (including spacing)
    """
    if not fb_is_initialized():
        return 0

    if cast[uint32](_font_data) == 0:
        text_init()

    # Get character code
    code: int32 = cast[int32](ch)

    # Check if character is in font range
    if code < _font_first_char or code > _font_last_char:
        code = 32  # Default to space

    # Calculate offset in font data
    char_idx: int32 = code - _font_first_char
    font_offset: int32 = char_idx * _font_height

    # Draw character
    row: int32 = 0
    while row < _font_height:
        bits: uint8 = _font_data[font_offset + row]

        col: int32 = 0
        while col < _font_width:
            if (bits & cast[uint8](1 << col)) != 0:
                # Draw scaled pixel
                if _font_size == 1:
                    fb_set_pixel(x + col, y + row, color)
                else:
                    _draw_scaled_pixel(x + col * _font_size, y + row * _font_size, _font_size, color)
            col = col + 1

        row = row + 1

    # Return width including spacing
    return (_font_width + 1) * _font_size

def text_draw_string(x: int32, y: int32, s: Ptr[char], color: uint32):
    """Draw a null-terminated string.

    Args:
        x, y: Starting position (top-left)
        s: Null-terminated string
        color: Text color
    """
    if not fb_is_initialized():
        return

    if cast[uint32](_font_data) == 0:
        text_init()

    cx: int32 = x
    i: int32 = 0

    while s[i] != '\0':
        ch: char = s[i]

        # Handle newline
        if ch == '\n':
            cx = x
            y = y + (_font_height + 1) * _font_size
        # Handle carriage return
        elif ch == '\r':
            cx = x
        # Handle tab (4 spaces)
        elif ch == '\t':
            cx = cx + (_font_width + 1) * _font_size * 4
        else:
            # Draw character and advance
            w: int32 = text_draw_char(cx, y, ch, color)
            cx = cx + w

        i = i + 1

def text_draw_int(x: int32, y: int32, n: int32, color: uint32) -> int32:
    """Draw an integer value.

    Args:
        x, y: Position
        n: Integer to draw
        color: Text color

    Returns:
        Total width drawn
    """
    # Build string from integer
    buf: Array[16, char]
    i: int32 = 0
    neg: bool = False

    if n == 0:
        buf[0] = '0'
        buf[1] = '\0'
    else:
        if n < 0:
            neg = True
            n = -n

        # Build digits in reverse
        while n > 0 and i < 14:
            buf[i] = cast[char](48 + (n % 10))
            n = n / 10
            i = i + 1

        if neg:
            buf[i] = '-'
            i = i + 1

        buf[i] = '\0'

        # Reverse the string
        j: int32 = 0
        k: int32 = i - 1
        while j < k:
            t: char = buf[j]
            buf[j] = buf[k]
            buf[k] = t
            j = j + 1
            k = k - 1

    text_draw_string(x, y, &buf[0], color)
    return text_measure(&buf[0])

def text_draw_hex(x: int32, y: int32, n: uint32, color: uint32) -> int32:
    """Draw a hexadecimal value with 0x prefix.

    Args:
        x, y: Position
        n: Value to draw
        color: Text color

    Returns:
        Total width drawn
    """
    buf: Array[12, char]
    hex_chars: Ptr[char] = "0123456789ABCDEF"

    buf[0] = '0'
    buf[1] = 'x'

    i: int32 = 9
    while i >= 2:
        buf[i] = hex_chars[cast[int32](n & 0xF)]
        n = n >> 4
        i = i - 1

    buf[10] = '\0'

    text_draw_string(x, y, &buf[0], color)
    return text_measure(&buf[0])

# ============================================================================
# Text Measurement
# ============================================================================

def text_measure(s: Ptr[char]) -> int32:
    """Measure width of a string in pixels.

    Args:
        s: Null-terminated string

    Returns:
        Total width in pixels
    """
    if cast[uint32](_font_data) == 0:
        text_init()

    width: int32 = 0
    max_width: int32 = 0
    i: int32 = 0

    while s[i] != '\0':
        ch: char = s[i]

        if ch == '\n':
            if width > max_width:
                max_width = width
            width = 0
        elif ch == '\r':
            pass
        elif ch == '\t':
            width = width + (_font_width + 1) * _font_size * 4
        else:
            width = width + (_font_width + 1) * _font_size

        i = i + 1

    if width > max_width:
        max_width = width

    return max_width

def text_measure_height(s: Ptr[char]) -> int32:
    """Measure height of a string in pixels (accounting for newlines).

    Args:
        s: Null-terminated string

    Returns:
        Total height in pixels
    """
    if cast[uint32](_font_data) == 0:
        text_init()

    lines: int32 = 1
    i: int32 = 0

    while s[i] != '\0':
        if s[i] == '\n':
            lines = lines + 1
        i = i + 1

    return lines * (_font_height + 1) * _font_size

def text_char_width(ch: char) -> int32:
    """Get width of a single character in pixels.

    Args:
        ch: Character

    Returns:
        Width in pixels (including spacing)
    """
    if cast[uint32](_font_data) == 0:
        text_init()

    if ch == '\t':
        return (_font_width + 1) * _font_size * 4

    return (_font_width + 1) * _font_size

# ============================================================================
# Text Drawing with Background
# ============================================================================

def text_draw_char_bg(x: int32, y: int32, ch: char, fg_color: uint32, bg_color: uint32) -> int32:
    """Draw a character with background color.

    Args:
        x, y: Position
        ch: Character to draw
        fg_color: Foreground (text) color
        bg_color: Background color

    Returns:
        Width of drawn character
    """
    if not fb_is_initialized():
        return 0

    if cast[uint32](_font_data) == 0:
        text_init()

    code: int32 = cast[int32](ch)
    if code < _font_first_char or code > _font_last_char:
        code = 32

    char_idx: int32 = code - _font_first_char
    font_offset: int32 = char_idx * _font_height

    row: int32 = 0
    while row < _font_height:
        bits: uint8 = _font_data[font_offset + row]

        col: int32 = 0
        while col < _font_width:
            color: uint32 = bg_color
            if (bits & cast[uint8](1 << col)) != 0:
                color = fg_color

            if _font_size == 1:
                fb_set_pixel(x + col, y + row, color)
            else:
                _draw_scaled_pixel(x + col * _font_size, y + row * _font_size, _font_size, color)

            col = col + 1

        row = row + 1

    return (_font_width + 1) * _font_size

def text_draw_string_bg(x: int32, y: int32, s: Ptr[char], fg_color: uint32, bg_color: uint32):
    """Draw a string with background color.

    Args:
        x, y: Starting position
        s: Null-terminated string
        fg_color: Text color
        bg_color: Background color
    """
    if not fb_is_initialized():
        return

    if cast[uint32](_font_data) == 0:
        text_init()

    cx: int32 = x
    i: int32 = 0

    while s[i] != '\0':
        ch: char = s[i]

        if ch == '\n':
            cx = x
            y = y + (_font_height + 1) * _font_size
        elif ch == '\r':
            cx = x
        elif ch == '\t':
            cx = cx + (_font_width + 1) * _font_size * 4
        else:
            w: int32 = text_draw_char_bg(cx, y, ch, fg_color, bg_color)
            cx = cx + w

        i = i + 1

# ============================================================================
# Helper Functions
# ============================================================================

def _draw_scaled_pixel(x: int32, y: int32, scale: int32, color: uint32):
    """Draw a scaled pixel (square of size scale x scale).

    Args:
        x, y: Top-left position
        scale: Size of square
        color: Pixel color
    """
    py: int32 = 0
    while py < scale:
        px: int32 = 0
        while px < scale:
            fb_set_pixel(x + px, y + py, color)
            px = px + 1
        py = py + 1
