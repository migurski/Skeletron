CFLAGS := -frounding-math 
INCLUDES := -I/usr/local/include

# on OSX:
# LIBS :=  -L/usr/local/lib -lCGAL -lboost_thread-mt

# on Ubuntu:
LIBS :=  -L/usr/local/lib -lCGAL -lboost_thread-mt -lcore++

dump-skeleton:
	g++ $(CFLAGS) $(INCLUDES) -o dump-skeleton dump-skeleton.cpp $(LIBS)
