#include "Tm2_FERMENTATION.h"

/***********************************************************************
* Function: Tm1_BREWING
* Abstract:
***********************************************************************/
Tm2_FERMENTATION::Tm2_FERMENTATION(BREWERY_BUFFER** brewbuff_, const int& arduinofd_){
	//
	arduinofd = arduinofd_;
	
	//initialize everything to off
	F_CompStatus = 0;

	//sensor vars
	F_Temp = 0.0;
	F_TempFil = 0.0;
	F_TMP36 = new TMP36(arduinofd,2,5.0);

	//define number of steps for mash infusion
	F_NumSteps = 1;
	F_TEMPPROFILE = new double[2];

	//step1
	F_TEMPPROFILE[0 *2+0] = 0.0;
	F_TEMPPROFILE[0 *2+1] = 60.0;

	#ifdef warn2
	ardprint("Loading buffer...",0);
	#endif
	brewbuff = brewbuff_;
	#ifdef warn2
	ardprint("Done.",1);
	#endif
}

/***********************************************************************
* Function: void Tm2
* Abstract: This is the task1 control function. This updates all of the
*	sensors and counters. Evaluates controls loops. Add switching times
*	for pumps and elements
***********************************************************************/
void Tm2_FERMENTATION::Tm2_FERMENTATION_EXE(double wtime_){
	wtime = wtime_;

	#ifdef warn2
	ardprint("Checking Fermentation Controls",1);
	#endif

/* Update Controls events in buffer */
	//get control time
	double ctrl_time; //holds current control time
	ctrl_time = (**brewbuff).get_next_time();
	#ifdef warn2
	ardprint("  CTRLTIME=",0);
	ardprint(ctrl_time,1);
	#endif
	//remove current event
	#ifdef warn2
	ardprint("  Removing current controls event...",0);
	#endif
	(*brewbuff) = (**brewbuff).remove_event();
	#ifdef warn2
	ardprint("Done.",1);
	#endif
	//insert new event
	#ifdef warn2
	ardprint("  Inserting new controls event...",0);
	#endif
	if ((*brewbuff) == NULL){//buffer is empty. need to create new buffer
		(*brewbuff) = new BREWERY_BUFFER(F_EVENT_CODE,0,ctrl_time+DelTm2);
		#ifdef warn2
		ardprint("Recreated Buffer.",0);
		#endif
	}
	else //buffer not empty. add normal event
		(**brewbuff).insert_event(F_EVENT_CODE,0,ctrl_time + DelTm2);
		#ifdef warn2
	ardprint("Done.",1);
	#endif
	#ifdef warn2
	(**brewbuff).print_buffer();
	#endif

/* Check Temperatures */
	#ifdef warn2
	ardprint("  Checking temperatures...",0);
	#endif
	F_Temp = (*F_TMP36).read_temp();
	#ifdef warn2
	ardprint("Done.",1);
	#endif

/*  Evaluate controls */
	#ifdef warn2
  	ardprint("  Evaluating mash tun controls...",0);
	#endif

	F_TempFil += (F_Temp-F_TempFil)*(DelTm1/(F_WTempFil)); 	//first-order lag filter on Mash Temperature
	F_TempErr  = (F_TempSet - F_TempFil); 					// calculate error from Mash set point and mash filter temperature

/* Update Element Switching Events in Buffer*/
	#ifdef warn2
	ardprint("  Inserting Compressor Switching Events...",0);
	#endif
	if      (F_TempErr < -5.0){
		if ((*brewbuff) == NULL){
			(*brewbuff) = new BREWERY_BUFFER(FCEVENT_CODE,TURNON*F_CompStatus,ctrl_time);
			#ifdef warn2
			ardprint("Recreated Buffer.",0);
			#endif
		}
		else
			(*brewbuff) = (**brewbuff).insert_event(FCEVENT_CODE,TURNON*F_CompStatus,ctrl_time);
	}
	else if (F_TempErr > +5.0){
		if ((*brewbuff) == NULL){
			(*brewbuff) = new BREWERY_BUFFER(FCEVENT_CODE,TURNOFF*F_CompStatus,ctrl_time);
			#ifdef warn2
			ardprint("Recreated Buffer.",0);
			#endif
		}
		else
			(*brewbuff) = (**brewbuff).insert_event(FCEVENT_CODE,TURNOFF*F_CompStatus,ctrl_time);
	}
	#ifdef warn2
	ardprint("Done.",1);
	#endif

	#ifdef warn2
        (**brewbuff).print_buffer();
	#endif

/* Print diagnotic information to terminal */

	#ifdef warn1
	ardprint("  F_Temp: ",0);
	ardprint(F_TempFil,0);
	ardprint("degF",0);

	ardprint("  F_TempSet: ",0);
	ardprint(F_TempSet,0);
	ardprint("degF",1);
	#endif

	#ifdef warn2
	ardprint("End Controls Loop",1);
	#endif

}

int Tm2_FERMENTATION::request(char request){
	if      (request=='0') return (int)wtime;
	else if (request=='1') return (int)F_TempFil;
	else if (request=='2') return (int)F_TempSet;
	else return 0;
}

void Tm2_FERMENTATION::command(char request, int setpoint){
	if      (request=='0') ;
	else if (request=='1') ;
	else if (request=='2') F_TempSet=setpoint;
}