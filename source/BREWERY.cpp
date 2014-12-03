//include headers files
#include "BREWERY.h"

//global variables
BREWERY_BUFFER*   brewbuff;
Tm1_BREWING*      Tm1_BREWING_1;
Tm2_FERMENTATION* Tm2_FERMENTATION_1;
double            wtime = 0.0;
int               arduinofd = -1;

//global enablers for major processes
char BREWERY1_ENB      = 1;
char FERMENTATION1_ENB = 0;

/***********************************************************************
* Function: void setup
* Abstract: function is automatically called in the arduino compilation
*	before the loop function is called. This sets up the serial connect
*	and the brewery buffer. Also initializes integrators.
***********************************************************************/
void setup() {
	#ifdef warn2
	ardprint("Start setup.",1);
	#endif
	
	wiringPiSetup();
	arduinofd = wiringPiI2CSetup(0x0A);
	if (arduinofd<0){
		ardprint("ERROR. COULD NOT CONNECT TO ARDUINO AT ",0);
		ardprint(0x0A,1);
	}
	else{
		ardprint("Initialized arduino on I2C at ",0);
		ardprint(arduinofd,1);
	}

	//setup serial and get time from arduino
	wtime = currenttime();//millis();

	//create controls objects
	#ifdef warn2
	ardprint("Create Tm1_BREWING.",1);
	#endif
	Tm1_BREWING_1      = new Tm1_BREWING(&brewbuff,arduinofd);
	#ifdef warn2
	ardprint("Create Tm2_FERMENTATION.",1);
	#endif
	Tm2_FERMENTATION_1 = new Tm2_FERMENTATION(&brewbuff,arduinofd);


	//initialize brewery controls event if brewery is commanded to be operational
	if (BREWERY1_ENB){
		#ifdef warn2
		ardprint("  Inserting new controls event...",0);
		#endif
		if (brewbuff == NULL){//buffer is empty. need to create new buffer
			brewbuff = new BREWERY_BUFFER(C_EVENT_CODE,0,wtime/1000.0+DelTm1);
			#ifdef warn2
			ardprint("Recreated Buffer.",0);
			#endif
		}
		else //buffer not empty. add normal event
			(*brewbuff).insert_event(C_EVENT_CODE,0,wtime/1000.0+DelTm1);
		#ifdef warn2
		ardprint("Done.",1);
		#endif
	}

	//insert fermentation chamber controls event
	if (FERMENTATION1_ENB){
		#ifdef warn2
		ardprint("  Inserting new controls event...",0);
		#endif
		if (brewbuff == NULL){//buffer is empty. need to create new buffer
			brewbuff = new BREWERY_BUFFER(F_EVENT_CODE,0,wtime/1000.0+DelTm2);
			#ifdef warn2
			ardprint("Recreated Buffer.",0);
			#endif
		}
		else //buffer not empty. add normal event
			(*brewbuff).insert_event(F_EVENT_CODE,0,wtime/1000.0+DelTm2);
		#ifdef warn2
		ardprint("Done.",1);
		#endif
	}

	//setup output pins
	pinMode(B_pin,OUTPUT);
	pinMode(P1pin,OUTPUT);
}

//define main function as loop for arduino or main for simulator
void loop() {
	char next_type; //stores next action type from the buffer

	/*if brewbuff is empty, some reference has been lost. the brewbuff should
	  always have at least a control action in the buffer at this point*/
	if (brewbuff==NULL){
		#ifdef warn0
		ardprint("SOMETHING BAD HAS HAPPENED. EXITING.",1);
		ardprint("Time is:",0);
		ardprint(wtime,1);
		#endif

		delay(100000);
	}

	//if the current time is past the next action, conduct next action
	if (double(wtime)/1000.0>(*brewbuff).get_next_time()){
		//print buffer on highest warning level
		#ifdef warn2
		(*brewbuff).print_buffer();
		#endif


		//determine next action and call appropriate function
		next_type = (*brewbuff).get_next_type();
		if      (next_type == C_EVENT_CODE) Tm1_BREWING_1->Tm1(wtime);
		else if (next_type == B_EVENT_CODE) B_ElemSwitch();
		else if (next_type == P1EVENT_CODE) P1PumpSwitch();
		else if (next_type == M_EVENT_CODE) Tm1_BREWING_1->MashTemp_Update();
		else if (next_type == F_EVENT_CODE) Tm2_FERMENTATION_1->Tm2_FERMENTATION_EXE(wtime);
		else if (next_type == FCEVENT_CODE) F_CompSwitch();
	}


	//update time
	wtime = currenttime();//millis();
	
	//return wtime;
}

void stopControls(){
	digitalWrite(P1pin,0);
	digitalWrite(B_pin,0);
}

/***********************************************************************
* Function: void B_ElemSwitch()
* Abstract: Switches state of boil element to commanded state
***********************************************************************/
void B_ElemSwitch(){
	#ifdef warn2
  	ardprint("Switching BOIL ELEMENT",1);
	#endif

	int switchdir;
	switchdir = (*brewbuff).get_next_act();
	digitalWrite(B_pin,switchdir);

	#ifdef warn2
	ardprint("  Removing current BOIL ELEMENT switching event...",0);
	#endif
	brewbuff = (*brewbuff).remove_event();
	#ifdef warn2
	ardprint("Done.",1);
	#endif
}

/***********************************************************************
* Function: void P1ElemSwitch()
* Abstract: Switches state of PUMP1 to commanded state
***********************************************************************/
void P1PumpSwitch(){
	#ifdef warn2
  	ardprint("Switching Pump",1);
  	#endif

  	int switchdir;
	switchdir = (*brewbuff).get_next_act();
	digitalWrite(P1pin,switchdir);

  	#ifdef warn2
	ardprint("  Removing current PUMP1 switching event...",0);
	#endif
	brewbuff = (*brewbuff).remove_event();
	#ifdef warn2
  	ardprint("Done.",1);
	#endif
}

/***********************************************************************
* Function: void F_CompSwitch()
* Abstract: Switches state of Fermentation Compressor to commanded state
***********************************************************************/
void F_CompSwitch(){
	#ifdef warn2
  	ardprint("Switching Compressor",1);
  	#endif

  	int switchdir;
	switchdir = (*brewbuff).get_next_act();
	digitalWrite(F_pin,switchdir);

  	#ifdef warn2
	ardprint("  Removing current Compressor switching event...",0);
	#endif
	brewbuff = (*brewbuff).remove_event();
	#ifdef warn2
  	ardprint("Done.",1);
	#endif
}

//BREWERY ACCESSORS
//get functions
double get_Tm1_BREWING_1_wtime()			{ return wtime; 							}
double get_Tm1_BREWING_1_B_TempFil()		{ return Tm1_BREWING_1->get_B_TempFil(); 		}
double get_Tm1_BREWING_1_B_TempSet()		{ return Tm1_BREWING_1->get_B_TempSet(); 		}
double get_Tm1_BREWING_1_B_ElemModInd()		{ return Tm1_BREWING_1->get_B_ElemModInd();		}
double get_Tm1_BREWING_1_M_TempFil()		{ return Tm1_BREWING_1->get_M_TempFil(); 		}
double get_Tm1_BREWING_1_M_TempSet()		{ return Tm1_BREWING_1->get_M_TempSet(); 		}
int    get_Tm1_BREWING_1_requestpermission(){ return Tm1_BREWING_1->get_requestpermission(); 	}
int    get_Tm1_BREWING_1_C_State()		{ return Tm1_BREWING_1->get_C_State(); 			}
double get_Tm1_BREWING_1_timeleft()		{ return Tm1_BREWING_1->get_timeleft();			}

//set functions
void set_Tm1_BREWING_1_B_TempSet(const double& _in1)		{ Tm1_BREWING_1->set_B_TempSet(_in1); 		}
void set_Tm1_BREWING_1_M_TempSet(const double& _in1)		{ Tm1_BREWING_1->set_M_TempSet(_in1); 		}
void set_Tm1_BREWING_1_grantpermission(const int& _in1)	{ Tm1_BREWING_1->set_grantpermission(_in1); 	}
void set_Tm1_BREWING_1_C_State(const int& _in1)			{ Tm1_BREWING_1->set_C_State(_in1); 		}
