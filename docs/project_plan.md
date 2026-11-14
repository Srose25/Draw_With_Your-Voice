# Draw With Your Voice

In this project we will simulate Cymatic plates and how they interact with sound waves. However, instead of simulating hundreds of thousands of particles, we want to build a program that can draw (much like MS paint) with anywhere from 1 - 12 particles. A key press will be able to determine whether the threaded particles are drawing on the canvas or not.


# Files:
 - main.py
 - particle.py (Class)
 - helpers.py (helping functions)
 - audio_producer.py (Class)
 - settings.py (Class)

## Features:
A small header at the top of the program will explain the controls of the program. In these controls you will be able to control the amount of particles that can be simultaneously active, what color you want to draw with, and brush size / style.

One final setting that will be critical to consider is the ability to turn off the microphone version of the program and alter the equation manually. The chladni plate has a few different different algorithms depending on the shape of the plate. We want to implement the physics of both the square plate and the circlular plate. This feature will be accessible through a button with a microphone icon, `"assets/microphone_icon.png"`, and when it is deactivated then you will have full control over all of the variables in the chladni equations. 

### Further Context on Implementation Features
**Multiple Threaded Particles:** The program must pause when you are selecting the number of particles to show on screen. The reason for this is because we'll want them equally spread out on the board for the best chance to draw in a similar way of a kaleidoscope. As soon as you have selected the number of particles to show on screen then they will display on the screen. Depending on how many particles you choose, the pattern in which they will appear will be different.

| Number of particles | The basic shape description: |
|---------------------|-------------------------------|
|1 Particle: | The One particle should be nearing the top of the window so it's not too close to the center.|
|2 Particles: |The second particle should be placed on the same x axis as the first, but will be closer to the bottom of the screen.|
|3 Particles: |The three particles will be placed in an equilateral triangular shape.(Two on the bottom and one on top.)|
|4 Particles: |Four particles should be placed in a square shape with a generous amount of space between the center and the edges.|
|5 Particles: |Five particles should be placed in a pentagon with generous spacing between the center and edges.|
|6 Particles: |Six particles will be represented by a hexagon with generous spacing although the particles will now be starting to get closer.|
|7 Particles: |Seven will be a bit different since there isn't a nice place to put it. We will keep the same hexagonal shape, but place a particle in the center.|
|8 Particles: |The 8 particled shape will be a basic octagonal shape with generous spacing.|
|9 Particles: |This is where things get a bit more creative. For the first 5 particles, we will retain the original pentagonal shape from before, but for our final four particles we will create a small square shape in the center of the board.|
|10 Particles: |This shape will follow the same inspiration as the 9 particle board however instead of a pentagon and square, it will be two pentagons. An outer and inner pentagon.|
|11 Particles: |Following this same line of thinking the outer layer of this one will be reminiscent of the 6 particled hexagon we made, with an inner pentagon.|
|12 Particles: |We will break away from the mold one last time for the final option. We will create a mid section for this one, bring a total of 3 layers. Each layer will have 4 particles each. The inner layer being in a square shape, the mid layer in more of a diamond orientation, and the outer layer being a square.|

**Chladni Equation and settings:** The program will calculate two different Chladni equations in order to calculate the position of our given particle threads. We will have the option to adjust the variables of our frequency when the microphone option is turned off, giving the user full customization. We will allow this customization through two specific equations which are the Square Plate and the Circular Plate. Here are the following equations for our plates in TeX Commands:

***Square Plate:***

`\cos\left(\frac{n \pi x}{L}\right) \cos\left(\frac{m \pi y}{L}\right) - \cos\left(\frac{m \pi x}{L}\right)
              \cos\left(\frac{n \pi y}{L}\right) = 0,`
where `n` and `m` are integers. This expression describes the nodal lines (i.e. the zeros) of a standing wave. Chladni patterns corresponding to values of `n, m` ranging from 1 to 8 are shown below. Note that the solution becomes trivial when `n = m`, and that the table of patterns is symmetric: the pattern for `(n_1, m_2)` is the same as that for `(n_2, m_1).`


***Circular Plate:***

 For a circular plate with radius `R` the solution is given in terms of polar coordinates `(r, 0)` by
`J_n(K \, r) \left(C_1 \cos(n \theta) + C_2 \sin(n \theta)\right),`

where `J_n` is the `n'th` order Bessel function. If the plate is fixed around the rim (e.g. a drum) then `K = Z_{nm} / R,` `Z_{nm}` is the `m'th` zero of the `n'th` order Bessel function. The term `"Z_{nm} r / R"` means the Bessel function term goes to zero at the rim as required by the constraint of the rim being fixed. 

**IMPORTANT!**

You must confirm the accuracy of the equations themselves before going any further. Compare them with 2 - 3 sources so they are as accurate as possible before translating them into python.

**Frequency Customization:**

This setting is mainly an accessibilty feature but it is critical that we have this in the implementation because if we have a bug with the microphone not working during our demo, then this will be our best shot. The customiztion will look like a slider that represents a range of 60 hz to 5000 hz, with presets that land on frequently used and heard frequencies. Here is a list of presets.

 - 60 hz
 - 120 hz
 - 220 hz
 - 440 hz
 - 528 hz
 - 880 hz

## File Breakdown

### main.py:
Main will handle the main game loop, draw the canvas, and hold any global variables that we need. In the game loop, we will call to other functions or call threaded classes to do other parts of the program. 

 - It will get the position of each particle and display that particle with a hollowed out circle using the draw function. 
 - If the E key is pressed down in the loop then the draw function will be called and will continue to draw until e is pressed again.
 - If C is pressed down in the loop then the screen will clear.
 - Needs to hold the state of our settings, meaning color / drawing settings, frequency settings if active, and particle settings.
 - When creating our threaded particle classes we need to pull from a data structure that has the (x, y) data for each particle in our given amount of selected particles.
 - In the game loop we need to call audio_producer.py which will continuously produce real time audio and process it into frequency and amplitude.

We need to import the sounddevice library found in the `sounddevice` folder.

**IMPORTANT!**

Before using this library I want you to read through the entire sounddevice folder and determine what files are vital to capturing audio input. Document your findings in a markdown file titled sound_device_essentials.md

### particle.py
Particle is a threaded class that will act as our cursor in the pygame loop. A particle will be visually represented by a hollow circle on the screen. It should replace the mouse input.

 - Each particle has an (x, y) value
 - That Value is subject to change based on the frequency and the equation that must be run during the simulation.
 - The particle will also hold the color, and brush size state as well, for if / when the draw function is called.
 - Two separate methods must hold the proper equation so it can be called for our simulation.
 - When the equation methods are called they will need real time audio data from sounddevice, or the audio data from the sine wave emulator.

### helpers.py
This is a file of helper functions that can be called upon later. Here is a list of functions that may be of some use.

| Function name | Purpose: |
| ------------- | -------- |
| Draw | While pygame has a draw function, we may want to create our own since we are doing this so unconventionally |
| Produce_Sine | This function would be useful for the custom sine wave feature. It would take the data from the sine frequency and actually produce an audible sine wave using pygame's audio capabilities. |
| Clear | Much like the draw function, this would be used to clear the screen |

### audio_producer.py
The Audio Thread (Producer): A background thread that continuously listens to the microphone using the sounddevice library. It captures raw audio buffers, runs a Fast Fourier Transform (FFT) using NumPy to break the audio down into frequency bins and amplitudes, and stores the latest spectrum data in a thread-safe variable.

### settings.py
This class will save the state of our settings. Here is the list of settings that we'll want to incorporate.

 - Brush Size
 - Brush Color
 - Brush Style
 - Number of Particles
 - Toggle Microphone
 - Sine Frequency Slider
 - Sine Frequency Presets

# Project Constitution

 - **Rule 1:** unknown is a valid answer, an invented fact is worse than uncertainty.
 - **Rule 2:** No AI agent will be allowed to stage, commit, or push anything to the repository.
 - **Rule 3:** Each design choice must be made by unanimous consensus among all Sub agents.
 - **Rule 4:** Each documented note must specify both the invariants of a proposed solution and blast radius of said solution.
 - **Rule 5:** While documenting, the agent must specify why a change was made and how the change was implemented
 - **Rule 6:** The agents will update the documents as code paths change in the code base to ensure accurate and up to date information.
 - **Rule 7:** No implementation of a proposed solution will be implemented until the review cycle is complete by way of unanimous consensus
 - **Rule 8:** No intentional tech debt. Build it right or don't build it.
 - **Rule 9:** No agent may implement a feature that hasn't been reviewed and approved with unanimous consensus.

