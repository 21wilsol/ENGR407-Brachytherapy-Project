Alex to include how to set up monte carlo stuff to get the sims running

To set-up the non - Monte Carlo based code a series of libaries are required, all of which are denoted at the top of the scripts during the "import" sections, these were installed via PIP, however any other install method should be acceptable.

To set-up the Monte Carlo based simualtions a series of steps has to be taken:

-Firstly, install docker, a system where the Monte Carlo data base and pre-requisites will all be stored

-Secondly, using command prompts install the specific Monte Carlo used (OpenMC), the following link from OpenMC also uses this method (https://docs.openmc.org/en/stable/quickinstall.html#installing-on-linux-mac-windows-with-docker)

-Thirdly, the correct version of python has to be installed as Docker and OpenMC use different versions. This project used Python 3.10 with all imports being for that version also

-Finally to run the code, it has to be run through the cmd window by accessing docker 
