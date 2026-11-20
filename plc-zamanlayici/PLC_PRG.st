(* CODESYS - PLC_PRG (Structured Text karşılığı)
   Ladder'daki 3 rung'ın birebir karşılığıdır.
   Network 1: TP  -> START  basılınca LED  10 sn yanar (darbe)
   Network 2: TON -> START2 10 sn basılı kalırsa LED2 yanar (gecikmeli açma)
   Network 3: TOF -> START3 bırakıldıktan sonra LED3 10 sn daha yanar (gecikmeli kapama) *)
PROGRAM PLC_PRG
VAR
    START, START2, START3 : BOOL;
    LED, LED2, LED3       : BOOL;
    TP_0  : TP;
    TON_0 : TON;
    TOF_0 : TOF;
    T0, T1, T2 : TIME;
END_VAR

TP_0 (IN := START,  PT := T#10S, Q => LED,  ET => T0);
TON_0(IN := START2, PT := T#10S, Q => LED2, ET => T1);
TOF_0(IN := START3, PT := T#10S, Q => LED3, ET => T2);
