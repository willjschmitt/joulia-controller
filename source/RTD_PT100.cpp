#include "RTD_PT100.h"

RTD_PT100::RTD_PT100(const int& fd_, const char& ain_pin_, const double& alpha_, const double& zeroR_, const double& aRef_, const double& k_, const double c_){
	fd      = fd_;
	ain_pin = ain_pin_;
	alpha   = alpha_;
	zeroR   = zeroR_;
	aRef    = aRef_;

	k = k_;
	c = c_;
}

double RTD_PT100::read_temp(){
	double counts;
	double Vdiff;
	double Vrtd;
	double Rrtd;
	double temp;

	counts = arduino_analogRead(fd, ain_pin);
	if (counts < 0.0) return -1.0;
	Vdiff  = aRef*(double(counts)/double(1024));
	Vrtd   = Vdiff*(15.0/270.0) + 5.0*(10.0/(100.0+10.0));
	Rrtd   = (1000.0*(1.0/5.0)*Vrtd)/(1.0-(1.0/5.0)*Vrtd);
	temp   = (Rrtd - 100.0)/alpha;
	temp   = temp*(9.0/5.0) + 32.0;
	temp   = temp*k + c;

	return temp;
}