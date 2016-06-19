#ifndef BREWERY_h
#define BREWERY_h

#include "stdfx.h"
#include "globals.h"
#include "Tm1_BREWING.h"
#include "Tm2_FERMENTATION.h"

#include "RTD_PT100.h"
#include "BREWERY_BUFFER.h"
#include "TMP36.h"

#ifndef noRPi
#include <wiringPi.h>
#include <wiringPiI2C.h>
#else
#include "wiringPi_mock.h"
#include "wiringPiI2C_mock.h"
#endif

extern int test();

//function prototypes for the main file
extern void setup();
extern void loop();
extern void stopControls();
extern void B_ElemSwitch();
extern void P1PumpSwitch();

extern void F_CompSwitch();


//BREWERY ACCESSORS
//get functions
extern double get_Tm1_BREWING_1_wtime();
extern bool   get_Tm1_BREWING_1_B_TempSet_lock();
extern double get_Tm1_BREWING_1_B_TempFil();
extern double get_Tm1_BREWING_1_B_TempSet();
extern double get_Tm1_BREWING_1_B_ElemModInd();
extern double get_Tm1_BREWING_1_M_TempFil();
extern double get_Tm1_BREWING_1_M_TempSet();
extern bool   get_Tm1_BREWING_1_M_TempSet_lock();
extern int    get_Tm1_BREWING_1_requestpermission();
extern int    get_Tm1_BREWING_1_C_State();
extern double get_Tm1_BREWING_1_timeleft();
extern bool   get_Tm1_BREWING_1_timeleft_lock();

//set functions
extern void set_Tm1_BREWING_1_B_TempSet(const double& _in1);
extern void set_Tm1_BREWING_1_B_TempSet_lock(const bool& _in1);
extern void set_Tm1_BREWING_1_M_TempSet(const double& _in1);
extern void set_Tm1_BREWING_1_M_TempSet_lock(const bool& _in1);
extern void set_Tm1_BREWING_1_grantpermission(const int& _in1);
extern void set_Tm1_BREWING_1_C_State(const int& _in1);
extern void set_Tm1_BREWING_1_timeleft(const double& newtime);
extern void set_Tm1_BREWING_1_timeleft_lock(const bool& lock);

#endif