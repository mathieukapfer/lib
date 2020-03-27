
SM_SOURCES=     machine.sm

# Uncomment to turn off IOStreams for debug.
NO_STREAMS=     -nostreams

# Uncomment to see state machine debug output.
#FSM_DEBUG=      -DFSM_DEBUG

# Uncomment to turn on debug message generation.
TRACE=          -g $(NO_STREAMS)

# Uncomment both lines to turn on serialization.
# SERIAL=         -serial
# SERIAL_FLAG=	  -DSERIALIZE

# Uncomment to turn off try/catch/rethrow generation.
# NO_CATCH=       -nocatch

# Uncomment to turn off exception throws.
# NO_EXCEPT=      -noex

# Uncomment to turn on static memory allocation.
# Note: this limits input strings to 10 characters to the
#       left of 'c'.
STACK=         -stack 10

# Uncomment to turn on CRTP code and -crtp SMC flag.
# CRTP=           -crtp
# CRTP_FLAG=      -DCRTP

# for WB projet
GEN=		..

SMC=            java -jar $(GEN)/smc_6_6_3/bin/Smc.jar
SMC_FLAGS=      -c++ $(TRACE) $(SERIAL) $(NO_CATCH) $(NO_EXCEPT) $(STACK) $(CRTP)



#################################################################
# Rules.
#

display: $(SM_SOURCES:%.sm=%_sm.dot)
	python $(GEN)/xdot.py $<

%_sm.dot :      %.sm
#		python $(GEN)/sm_dot.py $< full
		python $(GEN)/sm_dot.py $< light

%_sm.png :      %_sm.dot
		dot -T png -o $@ $<

graph :         $(SM_SOURCES:%.sm=%_sm.dot)

png :           $(SM_SOURCES:%.sm=%_sm.png)

clean :
		rm -rf *_sm.dot
		rm -rf *_sm.png
