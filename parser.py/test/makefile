all: images display

SM_SOURCES = cpw.sm

TOOLS=.

# Chosse the detail level
SMC_DISPLAY_LEVEL=0

# Choose the smc to dot converter
SMC2DOT=python ${TOOLS}/sm_dot.py 

# SMC
SMC=java -jar ${TOOLS}/smc/bin/Smc.jar
SMC_FLAGS= -c++ -g -nostreams
SMC_GRAPH_FLAGS= -graph -glevel ${SMC_DISPLAY_LEVEL}
DOT_TOOL = dot
SMC_DISPLAY=python ${TOOLS}/xdot.py

dotfile.ori: 
	$(SMC) $(SMC_GRAPH_FLAGS) $(SM_SOURCES);

dotfile: 
	${SMC2DOT} ${SM_SOURCES}

# generation maison (à améliorer)
display: dotfile
	 $(SMC_DISPLAY)  $(SM_SOURCES:.sm=_sm.dot)

# generation smc
display-ori: dotfile.ori
	 $(SMC_DISPLAY)  $(SM_SOURCES:.sm=_sm.dot)

# affichage du resultat attendu
display-joli: 
	 $(SMC_DISPLAY)  $(SM_SOURCES:.sm=_sm__joli__.dot)

images: dotfile
	$(DOT_TOOL) -Tjpg -o"$(SM_SOURCES:.sm=$(SMC_DISPLAY_LEVEL)_sm.jpg)" -Kdot $(SM_SOURCES:.sm=_sm.dot)
	$(DOT_TOOL) -Tpdf -o"$(SM_SOURCES:.sm=$(SMC_DISPLAY_LEVEL)_sm.pdf)" -Kdot $(SM_SOURCES:.sm=_sm.dot)
	$(DOT_TOOL) -Tjpg -o"$(SM_SOURCES:.sm=$(SMC_DISPLAY_LEVEL)_sm.png)" -Kdot $(SM_SOURCES:.sm=_sm.dot)

clean:
	-rm *_sm.*
