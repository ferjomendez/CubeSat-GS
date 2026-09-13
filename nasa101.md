National Aeronautics and
Space Administration
101
CubeSat
Basic Concepts and Processes for
First-Time CubeSat Developers
NASA CubeSat Launch Initiative
For Public Release – Revision Dated October 2017

101
CubeSat
Basic Concepts and Processes for
First-Time CubeSat Developers
NASA CubeSat Launch Initiative
For Public Release – Revision Dated October 2017

Produced under contract by the
California Polytechnic State University, San Luis Obispo (Cal Poly) CubeSat Systems Engineer Lab
Acknowledgements
This guide was produced by the following to support NASA’s CubeSat Launch Initiative:
NASA Advanced Exploration Systems Division
Writers and Contributors
Jason Crusan, NASA Headquarters
California Polytechnic’s PolySat Program,
Carol Galica, NASA Headquarters/Stellar Solutions
California Polytechnic State University—
San Luis Obispo
NASA Space Communications and Navigation Division
Jamie Chin
William Horne, NASA Headquarters Space
Roland Coelho
Communications and Navigation Spectrum
Justin Foley
Management
Alicia Johnstone
Ryan Nugent NASA Jet Propulsion Laboratory
Dave Pignatelli Charles Norton, Jet Propulsion Laboratory
Savannah Pignatelli Formulation Lead for Small Satellites
Nikolaus Powell
NOAA
Jordi Puig-Suari
Alan Robinson, NOAA Commercial Remote Sensing
NASA Launch Services Program Regulatory Affairs Office
William Atkinson, Kennedy Space Center
Jennifer Dorsey, Kennedy Space Center
Editors and Graphic Designer
Scott Higginbotham, Kennedy Space Center
Maile Krienke, Kennedy Space Center Communications Support Services Center
Kristina Nelson, Kennedy Space Center/ai Solutions Maxine Aldred, NASA Headquarters/Media Fusion
Bradley Poffenberger, Kennedy Space Center Andrew Cooke, NASA Headquarters/Media Fusion
Creg Raffington, Kennedy Space Center Tun Hla, NASA Headquarters/Media Fusion
Garrett Skrobot, Kennedy Space Center Michele Ostovar, NASA Headquarters/Media Fusion
Justin Treptow, Kennedy Space Center Jennifer Way, NASA Headquarters/Media Fusion
Anne Sweet, NASA Headquarters
For more information visit: http://go.nasa.gov/CubeSat_initiative
ii CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Table of Contents
Acknowledgments  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . ii Pictured above:
NASA mentors and the student launch
team for StangSat and PolySat go
1 Introduction 1 through final checks in the CubeSat lab
facility at Cal Poly. [VAFB/Kathi Peoples]
1.1 CubeSats . . . . . . . . . . . . . . . . . . . . . . . . 4
1.2 CubeSat Dispenser Systems . . . . . . . . . . . . . . 4
1.2.1 3U Dispensers 5
1.2.2 6U Dispensers 6
1.3 Launch Vehicles (LVs)—aka: Rockets . . . . . . . . . . 6
2 Development Process Overview 9
2.1 Concept Development (1–6 months) . . . . . . . . . 11
2.2 Securing Funding (1–12 months) . . . . . . . . . . . 11
2.3 Merit and Feasibility Reviews (1–2 months) . . . . . . 14
2.4 CubeSat Design (1–6 months) . . . . . . . . . . . . 15
2.5 Development and Submittal of Proposal in Response
to CSLI Call (3–4 months) . . . . . . . . . . . . . . . 17
2.6 Selection and Manifesting (1–36 months) . . . . . . . 18
2.7 Mission Coordination (9–18 months) . . . . . . . . . 19
2.8 Regulatory Licensing (4–6 months) . . . . . . . . . . 20
2.9 Flight-Specific Documentation Development and
Submittal (10–12 months) . . . . . . . . . . . . . . . 21
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative iii

CubeSat
101
Table of Contents
2.10 Ground Station Design, Development, and Testing
(2–12 months) . . . . . . . . . . . . . . . . . . . . . 22
2.11 CubeSat Hardware Fabrication and Testing
(2–12 months) . . . . . . . . . . . . . . . . . . . . . 23
2.12 Mission Readiness Reviews (Half-Day) . . . . . . . . 25
2.13 CubeSat-to-Dispenser Integration and Testing (2 days) 26
2.14 Dispenser-to-Launch Vehicle Integration (1 day) . . . . 27
2.15 Launch (1 day) . . . . . . . . . . . . . . . . . . . . 28
2.16 Mission Operations (variable, up to 20 years) . . . . . 29
3 Mission Models 31
3.1 NASA-Procured Launch Vehicle Mission Model . . . . 32
3.2 Operationally Responsive Space (ORS) Rideshare
Mission Model . . . . . . . . . . . . . . . . . . . . 34
3.3 National Reconnaissance Office (NRO) Rideshare
Mission Model . . . . . . . . . . . . . . . . . . . . 35
3.4 Commercial Launch Service Through a
Third-Party Broker Mission Model . . . . . . . . . . 37
ChargerSat-1’s mission was
3.5 International Space Station (ISS) developed by students from the
University of Alabama, Huntsville
Deployment Mission Model . . . . . . . . . . . . . . 38
to conduct three technology
demonstrations: a gravity gradient
stabilization system will passively
4 Requirement Sources for Launch 39 stabilize the spacecraft; deployable
solar panels will nearly double the
4.1 Mission-Specific Interface Control Documents (ICDs) . 40 power input to the spacecraft; and
the same deployable solar panels will
4.2 Launch Services Program (LSP)—
shape the gain pattern of a nadir-facing
Program-Level Requirements . . . . . . . . . . . . . 40
monopole antenna, allowing improved
4.3 CubeSat Design Specifications (CDS) . . . . . . . . . 40 horizon-to-horizon communications.
[University of Alabama, Huntsville]
4.4 Dispenser Standards/Specifications . . . . . . . . . 41
4.5 Federal Statutes . . . . . . . . . . . . . . . . . . . 41
4.6 Range Safety Requirements . . . . . . . . . . . . . 42
5 Licensing Procedures 43
5.1 Radio Frequency (RF) Licensing . . . . . . . . . . . 43
5.2 Remote Sensing . . . . . . . . . . . . . . . . . . . 51
iv CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Table of Contents
6 Flight Certification Documentation 53
6.1 Orbital Debris Mitigation Compliance . . . . . . . . . 54
6.2 Transmitter Surveys . . . . . . . . . . . . . . . . . . 55
6.3 Materials List . . . . . . . . . . . . . . . . . . . . . 55
6.4 Mass Properties Report . . . . . . . . . . . . . . . 56
6.5 Battery Report . . . . . . . . . . . . . . . . . . . . 57
6.6 Dimensional Verifications . . . . . . . . . . . . . . . 57
6.7 Electrical Report . . . . . . . . . . . . . . . . . . . 58
6.8 Venting Analysis . . . . . . . . . . . . . . . . . . . 58
6.9 Testing Procedures/Reports . . . . . . . . . . . . . 59
6.9.1 Day In The Life (DITL) Testing 59
6.9.2 Dynamic Environment Testing (Vibration/Shock) 60
6.9.3 Thermal Vacuum Bakeout Testing 62
6.10 Compliance Letter . . . . . . . . . . . . . . . . . . 64
6.11 Safety Package Inputs (e.g., Missile System Prelaunch
Safety Package, Flight Safety Panel) . . . . . . . . . 64
Appendices 65
A List of Abbreviations . . . . . . . . . . . . . . . . . 65
B Glossary . . . . . . . . . . . . . . . . . . . . . . . 66
C Templates . . . . . . . . . . . . . . . . . . . . . . 69
1. ODAR Inputs 69
2. CubeSat Components ODAR Template 71
3. Transmitter Survey 72
4. Materials List 74
5. Compliance Letter 77
6. CubeSat Acceptance Checklists 79
D Technical Reference Documents for CubeSat
Requirements. . . . . . . . . . . . . . . . . . . . . 84
E Notional Timeline of Events/Deliverables . . . . . . . 85
CCuubbeeSSaatt 110011:: BBaassiicc CCoonncceeppttss aanndd PPrroocceesssseess ffoorr FFiirrsstt--TTiimmee CCuubbeeSSaatt DDeevveellooppeerrss NNAASSAA CCuubbeeSSaatt LLaauunncchh IInniittiiaattiivvee v

CubeSat
101
1
Introduction IN THIS CHAPTER
1.1 CubeSats
1.2 CubeSat Dispenser Systems
1.2.1 3U Dispensers
1.2.2 6U Dispensers
1.3 Launch Vehicles (LV),
How do you start a CubeSat project? As popular as CubeSats have become, aka: Rockets
it’s surprising how little information is out there to help someone just enter-
ing the field. That’s why this document was created—to lay out everything you
Pictured above:
need to take a great CubeSat idea and make it into an actual spacecraft that is Launch of NASA’s National Polar-
launched into orbit. If you’ve been involved in the CubeSat world for a while, this orbiting Operational Environmental
Satellite System (NPOESS) Preparatory
guide will be a good reference for anything on which you might need a refresher.
Project (NPP) mission on Oct. 28,
However, this guide is written for first-time CubeSat developers, and especially 2011, which deployed five CubeSats
as part of the Educational Launch of
for CubeSats being developed at educational institutions. So, if this is your first
Nanosatellites (ELaNa)-III Mission. [U.S.
foray into CubeSats, you’ll want to read through carefully to get an idea of the
Air Force/Staff Sgt. Andrew Satran]
scope and the amount of work this project will require.
Before we get to the nitty-gritty, let’s start with a little
background. CubeSats began as a collaborative effort in
1999 between Jordi Puig-Suari, a professor at California
Polytechnic State University (Cal Poly), and Bob Twiggs, a
professor at Stanford University’s Space Systems Development
Laboratory (SSDL). The original intent of the project was
to provide affordable access to space for the university sci-
ence community, and it has successfully done so. Thanks
to CubeSats, many major universities now have a space
program. But it’s not just big universities; smaller universi-
ties, high schools, middle schools, and elementary schools
have also been able to start CubeSat programs of their own.
FIGURE 1 shows university students in their clean room taking
FIGURE 1: University student taking measurements of
measurements of a CubeSat they helped to develop. In addi-
a 2U CubeSat (CP9). [Cal Poly]
tion to educational institutions, Government agencies and
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 1

CubeSat
101
CHAPTER 1 Introduction
commercial groups around the world have developed CubeSats. They recognized
that the small, standardized platform of the CubeSat can help reduce the costs
of technical developments and scientific investigations. This lowered barrier to
entry has greatly increased access to space, leading to an exponential growth in
the popularity of CubeSats since their inception. In addition, this world of small,
affordable spacecraft has gotten more diverse and complicated each year, as more
and more researchers find utility in these small packages.
This document was created mainly for CubeSat developers who are working
with NASA’s CubeSat Launch Initiative (CSLI), but most chapters also will be
CubeSat developer: You’ll
hear this term a lot in the CubeSat
useful to CubeSat developers launching through other organizations.
world. This is the standard term for
any person or organization that is
What’s CSLI, you ask? CSLI is a NASA initiative that provides opportunities
designing, building, and preparing
for qualified CubeSats to fly as auxiliary payloads on future launches that have a CubeSat for flight.
excess capacity or as deployments from the International Space Station (ISS). In
very simple terms that means that NASA will cover the cost of providing your
CubeSat a ride to space in exchange for a report on the results of your CubeSat
investigation.
CSLI enables NASA to develop public-private partnerships that provide a low-
cost platform for NASA science missions, including planetary exploration, Earth
Illustration of ELaNa 23 RadSat-G
CubeSat from Montana State
University in orbit around Earth.
[Montana State University]
2 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 1 Introduction
observation, and fundamental Earth and space science.
These efforts are a cornerstone in the development of cut-
ting-edge NASA enabling technologies including laser
communications, next generation avionics approaches,
power generation, distributive sensor systems, sat-
ellite-to-satellite communications, and autonomous
movement. Leveraging these missions for collaboration
optimizes NASA’s technology investments, fosters open
innovation, and facilitates technology infusion. CubeSat
missions are enabling the acceleration of flight-qualified
technology assistance in raising Technology Readiness
Levels, which aligns to NASA’s objective of advancing
the Nation’s capabilities by maturing cross-cutting inno-
vative space technologies.
ARMADILLO (Attitude Related
Maneuvers And Debris Instrument in
About half of all CSLI missions are conducting scientific investigations, most
Low (L) Orbit) is a 3U CubeSat under
frequently Space Weather and Earth Science. Specific science investigation areas development at the University of
Texas at Austin. [University of Texas
include: biological science, study of near Earth objects, climate change, snow/ice
at Austin]
coverage, orbital debris, planetary science, space-based astronomy, and heliophys-
ics. Sixty-six percent of all CSLI missions are conducting technology develop-
ment or demonstrations. Communications, propulsion, navigation and control,
and radiation testing lead the topics in this area. Other notable technologies are
solar sails, additive manufacturing, femtosatellites, and smart phone satellites.
The low cost of development for a CubeSat allows for conducting higher risk
activities that would not be possible on large-scale NASA missions.
To be eligible for CSLI, your CubeSat investigation must be of clear bene-
investigation: This term gets
fit to NASA by supporting at least one goal or objective stated in the NASA
used often when talking about
Strategic Plan. This plan can be found on NASA’s Web site (http://www.nasa.
a CubeSat’s mission. It refers
gov). Each year—typically in early August—the CSLI solicits proposals through to the investigation, scientific or
an Announcement of Partnership Opportunity (AoPO) on the Federal Business otherwise, that your CubeSat will
be performing. In this context,
Opportunities Web site (https://sam.gov); proposals are typically due in
“investigation” is commonly used
November of that same year.
interchangeably with a CubeSat
“mission.”
If you’d like to read more about CSLI, their Web page can be found at http://
go.nasa.gov/CubeSat_initiative.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 3

CHAPTER 1 Introduction
1.1 CubeSats
Let’s explain what the “CubeSat” designation means,
compared to other small satellites. A small satellite is
generally considered to be any satellite that weighs less
than 300 kg (1,100 lb). A CubeSat, however, must con-
form to specific criteria that control factors such as its
shape, size, and weight.
The very specific standards for CubeSats help reduce
costs. The standardized aspects of CubeSats make it
possible for companies to mass-produce components
and offer off-the-shelf parts. As a result, the engineer-
ing and development of CubeSats becomes less costly
than highly customized small satellites. The standard-
ized shape and size also reduces costs associated with
transporting them to, and deploying them into, space. 1U Standard 3U Standard
Dimensions: Dimensions:
10 cm × 10 cm × 11 cm 10 cm × 10 cm × 34 cm
CubeSats come in several sizes, which are based on the
standard CubeSat “unit”—referred to as a 1U. A 1U FIGURE 2: 1U CubeSat CP1 (left)
3U CubeSat CP10 (right) [Cal Poly]
CubeSat is a 10 cm cube with a mass of approximately
1 to 1.33 kg. In the years since the CubeSat’s inception,
larger sizes have become popular, such as the 1.5U, 2U, 3U, 6U, and 12U.
Examples of a 1U and 3U are shown in FIGURE 2.
To get a better idea of the design requirements, take a look at the CubeSat Design
Specification (CDS) at http://www.cubesat.org. We’ll explain more about the
CDS and the documents you will need in the Requirements Sources chapter. For CDS: The CDS is a set of general
requirements for all CubeSats,
now, checking out the CDS at the CubeSat Web site is a great place to start your
but is not the official set of
preliminary design planning.
requirements that you will need to
follow for your launch.
1.2 CubeSat Dispenser Systems
We’ve described the CubeSat itself, but there’s another important piece of the
puzzle: the dispenser, which is the interface between the CubeSat and the
launch vehicle (LV). The dispenser provides attachment to a launch vehicle (or
rocket), protects the CubeSat during launch, and releases it into space at the
appropriate time.
4 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CHAPTER 1 Introduction
There are a number of different types of dispensers on the market. Each has
form factor: This is a term used
different features, but they are all designed to hold satellites that conform to the
to describe the size, shape, and/
standard CubeSat form factor. or component arrangement of a
particular device. When we use
Chances are you won’t be choosing the dispenser for your CubeSat; that honor it in reference to the standard
will go to whoever is footing the bill for the launch costs. It’s still important to CubeSat, we’re referring to the
specific size and mass that defines
understand the interface between your CubeSat and the launch vehicle. To that
a CubeSat.
end, this chapter will outline the types of dispensers with which you are likely
to work.
interface: “Interface” is a general
term that refers to any point
1.2.1 3U Dispensers
where two or more components
are joined together. For instance,
The first dispenser for CubeSats was
someone may ask, “How does
the Poly-Picosatellite Orbital Deployer the CubeSat interface with the
(P-POD). It was developed by Cal Poly, dispenser?” or, “Is there an
San Luis Obispo. The current revision electrical interface between the
CubeSat and the Dispenser?”
of the P-POD is pictured in FIGURE 3.
(These questions mean, “Can I
It can hold up to three Us of CubeSat
electrically connect the CubeSat
payload(s) (meaning any combination to the dispenser somehow?”)
that adds up to three Us, such as three
1Us, two 1.5Us, one 3U, etc.) and bolts
directly onto the launch vehicle. When FIGURE 3: Poly-Picosatellite Orbital payload: In the aerospace
it’s time to release the payload, the Deployer (P-POD) Developed by Cal industry, “payload” is a general
Poly, San Luis Obispo. [Cal Poly] term used to describe the cargo
launch vehicle sends an electrical signal
(e.g., a satellite or spacecraft)
to the P-POD, which causes the door
being delivered to space. When
to open and release the CubeSat(s) into we’re talking about CubeSat
orbit. Although most dispensers on the market have different designs, they all dispensers, the payload always
refers to the CubeSat.
tend to follow the same basic idea of a safe container with a door that opens at the
launch vehicle’s command, which then ejects the CubeSat into space.
In the beginning, the P-POD may have been the only option for CubeSats, but
now there are several dispenser choices. The manufacturers and vendors are easy
to find; just type keywords like “CubeSat dispenser” into your favorite search
engine and start clicking! Even though you might not have the final say in which
dispenser you use, you should take some time to understand the different dis-
pensers on the market and the kinds of features that are available before you start
designing your CubeSat.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 5

CHAPTER 1 Introduction
1.2.2 6U Dispensers
After a number of successful launches using the 3U dispenser,
developers quickly started planning for the next stage of
CubeSat design: let’s make them bigger! And thus in 2014, the
6U was born. The form factor of the 6U is essentially the same
as two 3Us side-by-side, making it twice as wide. You can see
an example of a 6U CubeSat in FIGURE 4. Multiple companies
within the industry have developed dispensers to accommodate
the larger size. And—you guessed it—those companies can be
found with a simple Internet search. The 6U dispensers’ fea-
tures vary, but most allow for any CubeSat configuration (e.g., FIGURE 4: Example of a 6U CubeSat
one 6U, six 1Us, two 3Us, etc.), and function similarly to the (Dellingr CubeSat) [NASA]
3U dispensers.
1.3 Launch Vehicles (LVs)—aka: Rockets
Finally, let’s talk about how the dispenser which contains your CubeSat will get
into orbit. CSLI contracts with multiple launch services that allow CubeSats to
hitch a ride. When the CubeSat/dispenser package was first dreamed up, the
idea was to bolt the dispenser onto the rocket where space was available. That is
still how most CubeSats make the journey, although there are now other options
Students Jacob Hambur and
Trisha Joseph from the University
of Central Florida constructing the
Q-PACE CubeSat. [University of
Central Florida]
6 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 1 Introduction
FIGURE 5: This United Launch Alliance (ULA) image shows where on the launch vehicle
the CubeSats might be located for a typical ULA CubeSat mission. The inset pictures
show a Naval Postgraduate School Cubesat Launcher Lite (NPSCul-Lite) housing eight
3U P-PODs and attached to the LV via an Aft Bulkhead Carrier (ABC) plate. [United
Launch Alliance]
available (see FIGURE 5). For example, a CubeSat can be sent with
the cargo on a resupply mission to the Space Station. The CubeSat
would be taken aboard the Space Station and released into space in
a specially designed deployer.
You also may forgo the dispenser altogether, like the Peruvian
Chasqui 1 did in 2014. During a spacewalk, a cosmonaut released
Chasqui 1 from the Space Station by tossing it by hand into orbit.
There’s even a video of this online! FIGURE 6 is a still from that video.
Keep in mind that although it has been done, this type of release is
extremely uncommon.
FIGURE 6: Russian cosmonaut preparing to launch
a 1U CubeSat that he is holding in his hand. [NASA]
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 7

CubeSat
101
CHAPTER 1 Introduction
U.S. Launch Vehicles Used for
CubeSat Launch
Super Strypi
Minotaur I
Minotaur IV
Taurus XL
58.3 m
Delta II
Antares
Falcon 9
Atlas V
Electron*
17 m
Falcon 9 Heavy*
LauncherOne*
Space Launch System (SLS)*
* These launch vehicles have not flown CubeSats as of
the writing of this document in 2017, but have included
CubeSats in the manifests of upcoming flights.
8 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative
Super
Strypi
Minotaur
I
Taurus
XL
Delta
II
Antares Falcon
9
Atlas
V
FIGURE 7: U.S. Launch Vehicles Used for CubeSat Launches.
FIGURE 7 shows all of the launch vehicles that have taken CSLI CubeSats to orbit
as of the writing of this document in 2017, as well as launch vehicles that are
planning to carry their first set of CubeSats on a future launch. Your CubeSat is
by no means limited to the launch vehicles included on this list; any rocket could
be a potential CubeSat launch vehicle given the right circumstances. The launch
vehicle has to have additional performance margin, be going to your desired
orbit, and can adapt to having dispensers installed.

CCuubbeeSSaatt
110011
2
Development IN THIS CHAPTER
2.1 Concept Development
Process Overview
2.2 Securing Funding
2.3 Merit and Feasibility Reviews
2.4 CubeSat Design
2.5 Development and Submittal of
Proposal in Response to CSLI Call
2.6 Selection and Manifesting
This chapter will tell you everything you need to accomplish and provide 2.7 Mission Coordination
2.8 Regulatory Licensing
an estimated timeline of how long it may take to get your CubeSat from
2.9 Flight Specific Documentation
a concept to a functioning satellite in orbit. We may be focusing on what you
Development and Submittal
need to do specifically for CSLI, but the process for any CubeSat mission will
2.10 Ground Station Design,
be very similar. The overall timeframe can vary depending on the launch vehicle Development, and Testing
selected and what you are trying to accomplish with your CubeSat. A CubeSat 2.11 CubeSat Hardware Fabrication
and Testing
can be designed, built, tested, and delivered in as little as 9 months, but typically
2.12 Mission Readiness Reviews
takes 18 to 24 months to complete. Once your CubeSat is ready to be delivered,
2.13 CubeSat-to-Dispenser Integration
the typical time to launch is anywhere from a few months to a few years. This
and Testing
is obviously affected by the availability of launch opportunities, but also by the 2.14 Dispenser-to-Launch Vehicle
flexibility of your orbital requirements—the more flexible, the easier to manifest Integration
and therefore, the shorter wait. Launch vehicles will usually require you to deliver 2.15 Launch
2.16 Mission Operations
your finished CubeSat between 4 weeks and 6 months prior to launch; again,
this depends on the launch vehicle provider and the organization sponsoring
your launch. Pictured above:
CSUNSat-1 Team (Adam Kaplan,
James Flynn, Donald Eckels) working on
The project phases (and typical timeframes) are as follows:
their CubeSat. [CSU-Northridge]
1. Concept Development (1–6 months)
mission: This term is a somewhat
2. Securing Funding (1–12 months)
generic, all-encompassing term that
3. Merit and Feasibility Reviews (1–2 months) refers to the enterprise as a whole.
It’s sometimes used interchange-
4. CubeSat Design (1–6 months)
ably with “project” or “investiga-
5. Development and Submittal of Proposal in Response to CSLI Call (3–4 months) tion” and includes all phases from
development, testing, integration, to
launch and operations.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 9

CubeSat
101
CHAPTER 2 Development Process Overview
6. Selection and Manifesting (1–36 months)
7. Mission Coordination (9–18 months)
Once this phase begins, a schedule will be provided by the integrator
that will dictate hardware and documentation delivery dates, essentially
providing the completion dates for the subsequent phases.
8. Licensing (4–6 months)
9. Flight-Specific Documentation Development and Submittal (10–12 months)
10. Ground Station Design, Development, and Testing (2–12 months)
11. CubeSat Hardware Fabrication and Testing (2–12 months)
12. Mission Readiness Reviews (half-day)
13. CubeSat to Dispenser Integration and Testing (1 day)
14. Dispenser to Launch Vehicle Integration (1 day)
15. Launch (1 day)
16. Mission Operations (variable, up to 20 years)
Note: FIGURE 8 and Appendix E provide a notional timeline of events and deliverables.
It will give you an idea of the timeframes that can overlap if your resources permit.
Concept Development
Funding
Merit/Feasibility Reviews
Develop/Submit Proposal
CSLI Selection Process
Manifesting
Mission Coordination
Licensing
Document Development/
Submission
Ground Station Development
and Testing
Flight Hardware Fabrication
Readiness Reviews
Dispenser Integration
Launch Vehicle Integration
Launch and Mission Operations
Months
FIGURE 8: This notional timeline shows how these phases might come together for a project.
10 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
2.1 Concept Development (1–6 months) >>FREE ADVICE
FLEXIBILITY IS KEY. Keep your
Okay, first things first: What do you want your CubeSat to do? As we mentioned
mission as flexible as possible.
in Chapter 1, it is important to choose a mission goal in which the CSLI, that is,
CSLI may select your CubeSat
NASA, will be interested. You may also consider choosing a concept for which mission because it has some
it will be easy to find funding. Many CubeSat missions are designed around the great science goals, but that
goals of a sponsor who will cover most of the development costs (more on that in doesn’t guarantee you’ll get a
launch right away. If you need
Chapter 2.2). For your best chance of being selected by CSLI, check off as many
special considerations like a very
“Keys to CSLI Selection” (see the “Free Advice” inset on the right) as you can.
specific orbit or specific launch
date, finding a launch could be
There’s no real time limit to this early concept development phase. Typically, a
tricky. Do your best to keep your
CubeSat developer will take anywhere from 1 to 6 months to plan the goals and requirements for launch as flexible
basic details of the CubeSat concept. as possible.
Keys to CSLI Selection
By the way, there’s no need to go it alone. Part of this conceptual development
• Adequate funding
time will be spent in search of possible partners and collaborators who may have
• Great merit and feasibility
goals similar to your own. This is called strategic partnering, and may provide reviews
you with extra funding or expertise, or both. • Clear demonstration of benefit
to NASA
2.2 Securing Funding (1–12 months)
strategic partnering:
WARNING! Sometimes a CubeSat mission
is too ambitious for a single
Under CSLI, NASA will cover all costs associated with the launch (up to organization to undertake. In
$300,000, typically enough to launch a 3U into low-Earth orbit), but CubeSat that case, a strategic partnership
developers selected for a CSLI flight are responsible for any and all can combine the strengths and
expenses related to the development and operation of the CubeSat. This resources of multiple organizations
includes all materials and labor required to build the CubeSat, plus the testing to achieve greater goals. These
expenses, ground station development and operational expenses, as well as strategic partnerships are typically
travel costs for required CSLI meetings and delivery. formalized by some kind of formal
agreement.
Money is very important. Once your CubeSat is selected and manifested for a
flight, CSLI will begin spending NASA dollars on your behalf. If you run out
of funds and cannot complete your CubeSat, NASA may not be able to apply
completed activities (“sunk costs”) to a replacement CubeSat. If this happens, a
launch opportunity will have been lost and it could even cause the demanifest of
other CubeSats co-manifested on the same launch. Additionally, the Cooperative
Research and Development Agreement (CRADA) that you sign with NASA after
being manifested requires you to reimburse NASA for any integration and launch
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 11

CubeSat
101
CHAPTER 2 Development Process Overview
costs incurred if you don’t deliver your CubeSat on time. This hasn’t happened to
anyone yet, but it could! Therefore, do not accept a launch opportunity until
you are confident you can deliver your CubeSat on time. As part of your pro-
posal to CSLI, you will need to provide enough budgetary information to prove
that you’ve secured enough funding to get you across the finish line.
That being said, there is plenty of money out there for CubeSat projects, you just
need to know where to look. Let’s take a look at where you can get the money you
need for your space mission!
Designing a CubeSat around a specific mission you came up with on your own
may be your dream, but it may be difficult to find funding. There are, however,
requests for proposals (RFPs) sent out every year from organizations looking for
people who can help them perform missions that would be perfect for a CubeSat.
The National Science Foundation has funded a number of CubeSats in the past,
Students Alex Diaz and Riki
as has NASA’s Earth Science Technology Office (ESTO). A simple Internet Munakata of California Polytechnic
State University testing the LightSail
search could help you find similar organizations looking for a great team to help
CubeSat. LightSail is a citizen-funded
them out. These organizations would work with your team and cover some or all technology demonstration mission
of the development costs. For university students interested in starting a CubeSat sponsored by the Planetary Society
using solar propulsion for CubeSats.
project, another option is to inquire with faculty and administrators at your col-
[The Planetary Society]
lege or university. Someone there may think that funding your project would be
an impressive feather in the university’s cap. In addition, every state has a NASA
Space Grant Consortium, which provides resources in support of students pur-
suing careers in science, technology, engineering, and mathematics, or STEM.
So, what’s the bottom line? How much is a CubeSat project going to cost?
Unfortunately, there isn’t a standard price tag we can show you. The amount of
funding you’re going to need to budget
for depends on a number of different
factors, the most important of which Common Costs Associated
with Developing a CubeSat
include the mission’s complexity, the
experience level of your personnel, the
project’s duration, and whether you
need any specialized hardware (see
FIGURE 9).
Materials Labor Environmental Travel
Before you start searching for fund-
Testing
ing, be sure to research the mission’s
requirements and create a detailed cost FIGURE 9: Common costs associated with developing a CubeSat.
estimate to avoid the pitfalls of being
12 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
DID YOU KNOW?
Crowdfunding
It’s probably crossed your mind already, and yes, crowdfunding is an option.
You may not be able to get all of the money you need through crowdfunding,
but CubeSat developers have used this method in the past. Just be aware that
what makes for a popular crowdfunding idea does not necessarily mean it is a
good CSLI idea.
One of the most successful crowdfunded CubeSats is LightSail, developed by
The Planetary Society (TPS). Carl Sagan was one of the founding members of
TPS, and now the famous science educator Bill Nye holds the reins as CEO.
LightSail is their flagship project. It’s a 3U CubeSat that is designed to unfurl a
32-square-meter sail, with the intent of propelling itself by sailing on the Sun’s
radiation. So far, one LightSail CubeSat has been launched as a technology
demonstration through CSLI. It’s an ambitious project—and according to
the Kickstarter Web site, LightSail-2 has raised over $1.24 million. Your team
might not have the media resources that TPS does (meaning you won’t get a
million dollars), but other teams have acquired more realistic amounts through
crowdfunding, so it could be a viable option for your team.
Technology Demonstration Missions
A number of CubeSat missions have been funded by Government agencies
or commercial organizations to perform technology demonstrations. For
example, say someone at NASA JPL is working on a $100 million satellite and
will include some brand new technology that hasn’t been to space yet. To lower
the risk to their own very expensive satellite mission, JPL will help someone KickSat is a technology
else to incorporate this new component on a CubeSat platform to take it for demonstration mission designed
an inexpensive test drive. This is an excellent option for newer organizations by Zachary Manchester of Cornell
and universities that want to get experience building CubeSats, but don’t have University to demonstrate the
deployment and operation of 104
significant resources.
Sprite “ChipSats” developed at the
university. KickSat was funded by
over 300 individual backers on the
underfunded. To build a cost estimate, start by looking online for component crowdfunding Web site KickStarter.
KickSat was launched by NASA’s
suppliers. That will help you get an idea of the costs of materials. We’ll include
CubeSat Launch Initiative on the
more details about components in the design chapter (Chapter 2.4). Funding will ELaNa V mission as an auxiliary
payload aboard the SpaceX-3 Cargo
also need to cover your ground station (see Chapter 2.10) and any environmental
Resupply Mission on April 18, 2014.
testing, which can include vibration, thermal vacuum bakeout, shock, and elec-
[Cornell University]
tromagnetic interference/electromagnetic compatibility (EMI/EMC) testing (See
Chapter 6 for test descriptions), plus anything else the launch vehicle provider
wants to throw at you. When possible, project reserves of at least 10% should be
part of the budget to address any unexpected events. One common cost that is
often overlooked is the cost for travel. CubeSat developers are typically required
to travel to at least one review, and later to deliver the CubeSat for integration
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 13

CubeSat
101
CHAPTER 2 Development Process Overview
into its dispenser. All of these items should be included in your cost estimate.
CSLI will only cover the costs of the launch, which include the CubeSat dis-
integration services: This
penser, the integration services, and the launch itself.
normally includes, at a minimum,
review of your deliverables,
the dispenser, integrating your
2.3 Merit and Feasibility Reviews (1–2 months)
CubeSat into the dispenser,
any testing that is done on the
As part of your proposal to CSLI, your team will be required to perform a merit dispenser/CubeSat system,
and physically integrating the
review and a feasibility review. These reviews help assure mission stakeholders
dispenser/CubeSat system onto
(and everyone else involved in the mission, i.e. CSLI, the launch vehicle provider,
the launch vehicle.
other sponsors, etc.) that your team or organization is capable of fulfilling your
obligations and completing a successful and worthwhile mission. Your team will
organize these reviews, and you will choose the reviewers. And to make sure
everything is on the up-and-up, the review panel must be made up of individ-
uals who are not on the project team. For the merit review, choose reviewers
who have knowledge/experience with your focus area (science, technology and/
or education) and that can assess why a flight opportunity is required. For the
feasibility review, choose reviewers ideally with knowledge of space flight and
spacecraft, but otherwise knowledgeable in various areas of hardware and project
development and that can assess your team’s ability to deliver your spacecraft on
time and on budget. If your focus area includes science or technology, be sure to
include someone knowledgeable on that specific area. Keep in mind that you are
not just trying to check a box; you want honest, valuable, and useful feedback to
Integration of the NRO’s Government
your objectives and design, so that you can improve your chances of a successful
Rideshare Advanced Concepts
proposal and successful mission. Experiment (GRACE) carrying
multiple payloads, which were
The exact details for these reviews will be stated in CSLI’s official call for propos- included as auxiliary payloads aboard
NROL-55. GRACE contained 13
als, but a basic synopsis is included here for your reference.
CubeSats, including 4 of NASA’s
CubeSat Launch Initiative CubeSats,
Merit Review as part of the ELaNa XII mission.
[Cal Poly]
Before submitting your proposal to CSLI, your CubeSat’s intended
mission must pass an intrinsic merit review. This review will assess
the goals and objectives of the mission to determine the quality of its
investigation in regard to science, education, and/or technology. It will
also determine if the overall investigation supports one or more of the
science, education, technology, and/or operations goals or objectives of
the NASA Strategic Plan. The more closely your mission aligns with a
goal or objective of the NASA Strategic Plan, the more likely it is that
your CubeSat will be selected.
14 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
Feasibility Review
In addition to the merit review, your team must also complete and
pass a feasibility review prior to submitting the proposal. This review
will judge whether your CubeSat’s mission is achievable with regard to
“technical implementation,” including feasibility, resiliency, risk, and
the probability of success. Bottom line: Is this mission even possible,
and can your team get it done?
CSLI is not only interested in the outcomes of the merit and feasibility
review but also how you addressed any findings from the reviews to resolve
any issues or concerns identified by the reviewers.
2.4 CubeSat Design (1–6 months)
You will probably begin your design process with a lot of research. CubeSats
have been around for a while now, and there are plenty of developers who have
already made mistakes from which you can learn. Most of these developers are
also very open and eager to share their successes and failures with others. There
is plenty of material published online that may prove useful to you. We would
also recommend attending one of the many annual conferences where you can
meet and chat with members of the CubeSat community. A problem that may
seem impossible to you might be old hat to someone who’s been working in this
field for a while.
You will also need to research which components will work best for your CubeSat
system. Luckily for you, CubeSats have become increasingly popular, and the
availability of commercial off-the-shelf parts has vastly increased. Although most
popular components can now be purchased through commercial vendors, many Students Sergei Posnov, David
educational organizations still try to build and design as many components as Einhorn, Thompson Cragwell, and
Maria Kromis are working on the
possible in-house in order to enhance the educational experience, as well as to
ANDESITE CubeSat from Boston
keep costs low. Because new companies are entering the marketplace every year, University. ANDESITE will measure
we can’t give you a complete list of CubeSat component vendors, but an Internet small-scale spatial magnetic features
in the auroral current systems. The
search will reveal a number of useful suppliers. A list of companies that sup-
measurements will be made through
ply CubeSat components can also be found at http://www.cubesat.org on the a constellation of picosatellites
deployed by the main payload and
Developer Resources page. The list on this page is updated regularly, but it isn’t
will communicate over a mesh
meant to be a complete list of every vendor on the market.
network. [Boston University]
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 15

CubeSat
101
CHAPTER 2 Development Process Overview
>>FREE ADVICE
KEEP IT SIMPLE. Keep the design as simple as possible. DOUBLE UP ON THAT BURN WIRE. You may not know what
CDS requirements are on the conservative side. burn wire is yet, but don’t worry, it’s a very simple (and
The CDS prohibits pyrotechnics, and discourages pretty reliable) method for constraining deployable
a host of other cool stuff. Some violations would be components. A lot of CubeSats use deployable solar
unacceptable, but some may be waived or approved panels to increase their Sun exposure, and virtually all
on a mission-by-mission basis. You will, however, CubeSats use some form of deployable antenna. Before
be eligible for more launches if you adhere to these the CubeSat is released into orbit, these deployables
specifications. Things like a propulsion system may need to be constrained. The most common method
make the launch provider or their primary payload to constrain a deployable is to tie a fishing line to its
nervous, and some just choose not to carry CubeSats component and route the other end around a simple
that have them. So CSLI may still select your CubeSat resistor, also called the burn wire. When it’s time to
for launch but it may take longer to find a willing launch release the deployables, a current is run through the
provider to give you a ride. resistor. When the resistor produces enough heat, the
fishing line melts and releases the deployable. The
IMPORTANT COMPONENTS SHOULD BE ON THE EXTERIOR. No only problem with this method is that sometimes the
matter how well you plan and design your CubeSat, it’s fishing line comes loose during vibration testing or
almost certain that something will break. Usually this ascent. Launch providers hate that. Use two separate
happens during environmental testing (i.e., vibration/ burn wires to give yourself, and the launch providers,
shock testing). This is normal for a new design, but some peace of mind. It should reduce the likelihood of a
there are things you can do to make the repair work deployable coming loose prematurely during testing.
simpler and quicker. Most of the time, if you need to fix
something on the inside of your structure (i.e., remove USE FAMILIAR COMPONENTS. Whenever possible, choose
panels and take things apart), you will be required to major components that have flown on CubeSats before.
perform certain testing again. However, if you design Major components include batteries, antennas, and
your CubeSat so that important components are near attitude determination and control systems (ADCS). You
the exterior and easy to access, then the rework may be aren’t restricted to using components that have flight
simple and retest might not be necessary. heritage, but it reduces the risk of failure and gives the
launch provider more confidence that your CubeSat
DO NOT DESIGN TO THE LIMITS OF THE ENVELOPE. The won’t create problems.
CDS defines the standard CubeSat “envelope”—that
is to say, the length, height, and width dimensions of USE UL LISTED BATTERIES. If a battery is “UL listed” it
the CubeSat body—very specifically. It’s extremely means that the company UL, LLC, has given this battery
important that your CubeSat measurements fall its stamp of approval, which is recognized industrywide.
within the tolerances set in the CDS. If your CubeSat UL puts batteries through a specific round of testing that
doesn’t fit, it doesn’t fly. It’s a pretty terrible feeling shows the batteries are reliable and meet certain industry
to deliver your satellite and find out it won’t fit in the specifications (i.e., environmental, testing to predetermine
dispenser, so make sure your design targets the optimal levels). Developers across the board prefer to use
dimension measurement, and the rest will be down to UL-certified batteries. If you use a battery without the UL
manufacturing. Pay attention to any planned protrusions certification or try to make your own battery, the launch
as well. The CDS allows protrusions from the CubeSat provider will require you to perform extra testing on your
body up to 6.5 mm from the surface. Most deployers batteries to prove their robustness. The same goes if you
can accommodate something a little longer, but that’s tamper with a UL listed battery or its safety features.
a dangerous path to walk. Simply put, as long as your
CubeSat stays within the dimensional bounds of the USE OF HIGH-MELTING POINT MATERIALS. (See inset in
CDS, there should be no problem when you deliver it. Chapter 6.1)
16 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
You’ll want to get started on your design as soon as possible. Depending on the
level of expertise of your team, you will encounter a number of setbacks during
development, so it’s very prudent to give yourself as much time as possible.
ADCS: The ADCS is the system
designed to stabilize and orient
To help you avoid some of those setbacks, we’ve started a list of design consid-
the CubeSat toward a given
erations for you to check out. (See Free Advice on the preceding page.) Almost
direction. This is a critical system
everything on this list is derived from real-world experiences and mishaps that for mission success. If the satellite
have cost developers valuable time and have given everyone involved extra truck- needs to point its solar panels
toward the Sun to get the most
loads of stress.
power possible or if you are taking
images of the Earth its attitude has
to be set to the correct value.
2.5 Development and Submittal of Proposal in
Response to CSLI Call (3–4 months)
We won’t get into too much detail about what needs to be in your proposal. The
specific proposal instructions for any Announcement of Partnership
Opportunity (AoPO) sent out by CSLI are detailed in the official
announcement posted at https://sam.gov or http://go.nasa.gov/
CubeSat_initiative. Timelines may vary, but proposals are usually due within 4
months of the AoPO being posted. Typically, the AoPO is posted in early
August and the proposals are due in November. Instructions on how to submit
the proposal are included in the AoPO. Typically, CSLI requests that the proposal
be e-mailed to a specific NASA representative.
It’s extremely important to follow the AoPO instructions, and to include all of
The St. Thomas More Cathedral
the requested information in your proposal. If the CSLI proposal evaluation School (STM)Sat-1 mission is
team finds that your proposal is not compliant with the AoPO, or is lacking an education mission to provide
hands-on, inquiry-based learning
any of the information required by the AoPO, then your proposal will be
activities with an on-orbit mission
removed from consideration for that selection period. You will need to rework to photograph Earth and transmit
your proposal and resubmit it to a future AoPO in a subsequent year. images. STMSat-1 was the first
CubeSat launched for a primary
school. It was launched by NASA’s
Remember when writing your proposal to emphasize how your CubeSat mis-
CubeSat Launch Initiative on the
sion satisfies all of the points listed in Keys to CSLI Selection in Chapter 2.1. December 6, 2015 ELaNa IX mission
on the fourth Orbital-ATK Cygnus
Commercial Resupply Services (CRS)
When submitting your proposal to CSLI, you will be asked to denote your project’s
to the Space Station and deployed
focus area(s): science, technology investigation and/or education. If you choose to on May 16, 2016. [St. Thomas More
select more than one focus area, your proposal and reviews must address the goals Cathedral School]
and objectives you will be meeting for each focus area. For example, if you choose
science and education, your proposal will be reviewed equally for the quality of
your science investigation and your education outcomes described in your sub-
mission. Using this example, a proposal with a strong science investigation could
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 17

CubeSat
101
CHAPTER 2 Development Process Overview
receive a substantially lower review if the proposal doesn’t contain an equally
strong education plan. Therefore, choose wisely and conservatively.
After the CubeSat has been selected it will be manifested on a mission. At that
time NASA and the CubeSat developer will enter into a contract with a lot
of legal jargon (e.g., liability, risk, data-sharing, etc.). This contract is called a
CRADA, which stands for Cooperative Research And Development Agreement.
NASA will write up this contract and send it to you, the CubeSat developer.
But because there are real legal consequences involved with this contract, you A set of NanoRacks CubeSats is
photographed by an Expedition 38
are strongly advised to have a legal expert review it with you. Most CubeSat
crew member after the deployment
developers send it to their sponsoring institution’s legal department. In the case by the Small Satellite Orbital Deployer
of university CubeSat projects, the university’s legal department typically reviews (SSOD). [NASA]
the agreement.
2.6 Selection and Manifesting (1–36 months)
Once proposals have been submitted, CSLI’s Selection Recommendation
Committee will determine which proposals meet all of the standards outlined in
the AoPO and will create a prioritized list of the qualifying CubeSat projects.
How do you get your CubeSat to the top of the priority list? First, your merit and
feasibility reviews need to look great. Second, make sure your proposal hits all
manifesting: The process
of the points in Chapter 2.1 Keys to CSLI Selection. Third, make sure your pro- of assigning CubeSats to the
posal clearly shows how you contribute to meeting one or more goals/objectives available slots on a launch
in the NASA Strategic Plan. Your proposal needs to be interesting and—if at all opportunity.
possible—groundbreaking.
Having priority doesn’t mean you’ll be manifested on the next CSLI launch,
because you still need to be matched with a launch that will work for your mission
parameters. However, having priority over the other CubeSat teams means you
get “dibs” on the first launch that matches your criteria. NASA Launch Services
Program (LSP) will pair the selected CubeSats with launch opportunities that are
best suited for the CubeSats’ missions and completion dates, taking into account
the planned orbit and any special constraints the CubeSat’s mission may have.
Once the CubeSats are paired and manifested, an ELaNa mission number will
be assigned.
The prioritized selection list will be released approximately 12 to 16 weeks after
the proposal deadline. Prior awards can be viewed at the NASA CSLI Web site.
18 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
2.7 Mission Coordination (9–18 months)
Let’s talk about mission coordination. This is another term that’s very common in
mission integrator: You may be
the aerospace industry, but not so much in other fields. When any undertaking
asking yourself why the mission
involves more than one party, a certain amount of “coordination” is required.
integrator isn’t called the mission
CubeSat missions involve, at the very least, a CubeSat developer and an LV pro- coordinator. Well, sometimes
vider. The missions that CSLI sponsors will typically include a mission inte- they are. The terms “integration”
and “coordination” when referring
grator, who is responsible for the coordination. A mission integrator is assigned
to a mission are commonly used
once a launch opportunity is identified and one or more CubeSats are mani-
interchangeably. For the purposes
fested to that opportunity. Note that the term “mission” here is bigger than your
of this document, the person/
CubeSat “mission.” The mission now represents your CubeSat plus any other co- organization responsible for the
manifested CubeSats, the dispensers, the launch, and the deployment. This coor- coordination will be referred to as
“mission integrator,” and we’ll use
dination includes managing integration schedules, deliverable documentation,
“mission coordination” to refer to
and how the requirements will be verified. In other words: mission coordination
mission coordination activities.
is a catchall term for the overall mission planning and the submitting and keep-
ing track of paperwork that will be required to pass between the LV provider and
the CubeSat developer. The mission integrator will be responsible for the sched-
ule and communication between the parties to make sure all CubeSat require-
ments are verified on time.
Mission coordination will begin about 18 months before the scheduled launch
date. It will start with a “kickoff” meeting between all of the developers on the
mission and the mission integrator. Don’t worry, you shouldn’t need to travel any-
where for this; the kickoff will be conducted over the phone as a teleconference
(also called a “telecon”). The CubeSat developers aren’t expected to know all of deliverables: A deliverable
the ins and outs of the requirement verification process, so the mission integrator is anything that your team has
agreed to submit to the mission
will help guide the developers through the process. The mission integrator will
integrator as part of your legal
supply the developer with a schedule for hardware and document deliverables,
obligations under the CRADA.
and document templates for each document deliverable. The mission integrator These deliverables will be used to
is also responsible for creating a mission-specific CubeSat-to-dispenser Interface verify that your CubeSat meets the
Control Document (ICD)—check out the ICD in Chapter 4.1 for more details. requirements set in the mission
ICD. Chapter 6 describes the
This ICD is, essentially, the official rulebook for your CubeSat. You and the
deliverables required on a typical
mission integrator will work together to show that your CubeSat meets every
CubeSat mission.
one of the requirements stated in the ICD. These requirements are derived from
the CDS and the launch vehicle’s specific needs. The ICD will also specify the
relevant environmental testing levels and durations to which your CubeSat will
need to be tested. To help keep everyone on track, the mission integrator will
organize regular telecons to discuss the current status of the mission, get CubeSat
development updates, and provide technical assistance and guidance.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 19

CubeSat
101
CHAPTER 2 Development Process Overview
During this mission coordination phase, your team will be working on hardware
fabrication and design, testing, and the documentation you will be submitting to
the mission integrator.
2.8 Regulatory Licensing (4–6 months)
We’ll go into much more detail about regulation-related licensing in Chapter
5, but we’ll explain the basics here. All CubeSats must go through a licensing
process in order to transmit radio signals and a separate process to license the use
of an imaging instrument such as a camera. Obtaining licenses for satellites
can be a lengthy process. Prior to finalizing any system design and opera-
tions plan and before submitting any application,
you should understand regulatory constraints and
clearly identify all necessary information required
for licensing. Once all the necessary information
is documented, you should submit your applica-
tion, as soon as possible, preferably within 30 days
after your CubeSat gets manifested or earlier. If you
don’t have all of the necessary licenses in hand prior
to your CubeSat’s final delivery date to the integra-
tor, you risk your CubeSat being demanifested from
the mission. This means you will be bumped from the
launch. Don’t let that scare you too much; as long as
you comply with regulatory rules, prepare a complete
application, and get your paperwork started early, as
recommended here, there should be time to get your
license granted.
More than likely, you will need to obtain a radio license because your CubeSat, Naia Butler-Craig, a systems engineer
intern at NASA’s Glenn Research
like most other satellites, probably needs to transmit on a radio frequency (RF)
Center, works on assembling and
to communicate with the ground and Federal law requires a radio license for testing the Advanced Electrical
that. Licenses to transmit RF to or from U.S. Government operated satellites are Bus (ALBus) CubeSat. The ALBus
CubeSat is a pathfinder technology
handled by the National Telecommunications and Information Administration
demonstration for high power density
(NTIA), while the Federal Communications Commission (FCC) handles all CubeSats. [NASA/Bridget Caswell,
other non–Federal Government agency operated satellites. Before you get started, Alcyon Technical Services]
see Chapter 5 to help you determine which agency, and which license, is appro-
priate for your CubeSat and its mission.
20 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
The second license you may have to obtain is based on whether your CubeSat
includes an imager, or camera. Anyone who intends to operate a non–Government
owned U.S. CubeSat with an imager must contact the National Oceanic and
Atmospheric Administration (NOAA) to find out whether a remote sensing
license is necessary, and if it is, to get the application process started. This process
can be lengthy, and the FCC will need to see your license from NOAA before it
will finish processing your RF license. Many more details on obtaining a NOAA
license can be found in Licensing Procedures (Chapter 5).
WARNING!
Being demanifested for a licensing issue sounds scary, and it is. The
regulatory agencies take this very seriously. There was a CubeSat on an early
CSLI launch that had been integrated into the dispenser, and onto the launch
vehicle, without an approved FCC RF license. CSLI and the integrator had
assumed it would be granted before launch, but a few days before launch
this still hadn’t occurred. There wasn’t time to remove the CubeSat from the
dispenser, so the integrator was planning to go to the launch vehicle and
disable the release mechanism, so that the CubeSat could not be released into
orbit. Luckily for the CubeSat developer, the license came through just before it
was too late. Otherwise, not only would their mission have been scrubbed,
but they also would have lost their CubeSat!
2.9 Flight-Specific Documentation Development
and Submittal (10–12 months)
Once your CubeSat is manifested on a launch, the mission integrator will provide
a list of deliverables (documents that CSLI and the mission integrator need from
your team) that will need to be completed and submitted by a specified date.
These documents will be used to verify that your CubeSat meets all safety and
launch requirements set by the ICD. The first of these documents will likely be
due shortly after your first kickoff meeting with the mission integrator. These
deliverable documents will be discussed in more detail in the Flight Certification
Documentation section (Chapter 6) of this document.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 21

CubeSat
101
CHAPTER 2 Development Process Overview
2.10 G round Station Design, Development, and
Testing (2–12 months)
You will need a way to communicate with your CubeSat once it’s in space. For
that you need a ground station. There are a lot of components required for a
proper ground station, but two basic components you will need are a radio and
an antenna. Your ground station should be built early in your project’s timeline.
If your team isn’t experienced with CubeSat communications and the hardware
required, building and testing your ground station will consume a lot of time
and energy. Most teams prefer to use off-the-shelf amateur radio components,
and there are typically local amateur radio club members willing (excited, even)
to advise and help with building and commissioning the ground station. You can
find these types of groups online (i.e. American Radio Relay League http://www.
arrl.org/). Some good basic design information also can be found on http://www.
Anthony Young works in the ground
cubesat.org. station at Santa Clara University,
Santa Clara, Calif., in support
of NASA’s Organism/Organic
Thorough testing of the ground station is critical for your mission’s success. The
Exposure to Orbital Stresses
ground station is used to locate the satellite as well as to send commands and to (O/OREOS) CubeSat. [NASA]
downlink data. Launching with an inadequate ground station is a mission killer.
Your ground station should be tested early and often. By monitoring existing sat-
ellites, your team can gain experience operating the equipment. This experience is
invaluable in the satellite building process, particularly when writing the software
and command structure. Additionally, it’s important to have your ground station
in the loop during development. There are many satellites (CubeSats, amateur
satellites, NOAA satellites, Space Station, etc.), which can be tracked, and even
commanded if you coordinate with the satellite’s operators. Participating in such
>>FREE ADVICE
terminal node controller
TROUBLESHOOTING BASICS. The ground station has many components (TNC): The TNC is a device used
operating independently, any of which, if not working properly, can cause by amateur radio operators to
communication issues. When troubleshooting, take a systematic approach. participate in AX.25 packet radio
Make sure antennas are pointing where expected by using calibration networks. It will assemble the
points like mountains, the Sun, or the Moon for azimuth and elevation. data into packets of information
Use a vector network analyzer, if available, to check the impedance of the and key the transmitter to send
antenna, cables, and any adapters in the path to the radio. Also confirm that the packets of data to the ground
the radio is tuning to the expected frequency, is in the right mode, and that station. Once the ground station
line levels are appropriately set between the radio and the terminal node receives the packets, the packets
controller (TNC)/ computer. Software defined radios, particularly the small, are reassembled and encoded to
less expensive options like the RTL2832 or FunCube, are an excellent way to a form that can be interpreted by
capture and replay slices of RF spectrum for later decoding practice. your ground station.
22 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
activities can be valuable experience for your CubeSat team. (See Chapter 2.16 for
more on tracking satellites).
Your team should become familiar with commonly tracked satellites and their
operating modes and frequencies. In the 437 MHz (70 cm) band there are plenty
of CubeSats with beacons strong enough to easily receive, but it is necessary
to know which ones are active and which are not. As a rule of thumb, look for
recently launched CubeSats, as those are most likely to be operating. Contact the
organization that developed (and is most likely operating) the CubeSat, if nec- margin: This is a very common
essary, to confirm operation. In the 140 MHz (2 m) band, the NOAA weather term in the engineering world
specifically referring to the safety
satellites are an excellent test object and produce interesting images.
margin, but is more generally
used to refer to extra anything that
On your launch day, you’ll want to be as knowledgeable about CubeSat com-
gives you peace of mind. When
munications (CubeSat comms) and satellite tracking as humanly possible, so do
you’re talking about scheduling,
as much research as you can. This includes contacting experienced university you add time, or margin, in case
CubeSat programs, reading papers and presentations online, and going to small you run into issues or just estimate
incorrectly.
satellite conferences to chat with your fellow developers. With all of the resources
available to you, you shouldn’t have too much trouble getting your team up to
speed before launch. ETU: An engineering test unit.
An ETU is built like the flight unit,
but is not intended for launch.
2.11 CubeSat Hardware Fabrication and Testing
Developers will typically use the
(2–12 months) ETU like a practice dummy. It can
be used to practice putting the
components together, fit checks,
As mentioned in the CubeSat Design section (Chapter 2.4), many hardware com-
hardware and software testing,
ponents may be purchased from commercial vendors, but fabricating in-house
and anything else that you don’t
whenever possible can help keep costs down and, for educational CubeSat proj- want to try for the first time on
ects, can increase learning opportunities. The timeframe for this part of the your valuable flight unit.
process varies greatly depending on how ambitious the design is and how expe-
rienced your team is. Be conservative in planning and pad your build schedule
FlatSat: A FlatSat is exactly what
with plenty of margin.
it sounds like. It’s an engineering
unit of the CubeSat that includes
Keep in mind that it’s cheaper to build two satellites at once than to build one all of the components, except
and later decide to build another. Launch opportunities are very fluid, and launch the structure. Typically, the
failures are always possible. If financially possible, it is extremely useful to build components are mounted on
some sort of flat board, hence
multiple units (e.g., one Engineering Test Unit—known as an ETU, a FlatSat,
the term FlatSat. Developers
and two flight units). Qualification testing and integrated development can be
can use the FlatSat to test and
performed on the ETU, troubleshooting on the FlatSat, and final environmental troubleshoot the CubeSat’s
testing can be done on the flight units. No two satellites are exactly the same, so systems without integrating
building two flight units gives the option to fly the best hardware. everything onto the structure.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 23

CubeSat
101
CHAPTER 2 Development Process Overview
During assembly of the flight satellites, developers are encouraged to take as
many pictures as possible at regular intervals. Keeping detailed photo documen-
tation during all phases of assembly, integration, and testing has saved some flight
missions in the past. We can’t stress enough how important it is to keep good,
detailed records of your successes and failures as you progress. One of the most
common problems CubeSat teams have had is losing knowledge and expertise
when team members move on and are replaced by new personnel. University
CubeSat developers have the greatest problem with senior members graduating
before the completion of the project.
Denise Thorsen and Jesse Frey from
the University of Alaska Fairbanks
are performing DITL testing on the
>>FREE ADVICE
Alaska Research Center (ARC)
CubeSat. ARC was launched by
KEEP EXCELLENT RECORDS OF EVERYTHING YOU DO. It is incredibly important
NASA’s CubeSat Launch Initiative on
to keep great records of the work your team has been doing. These the ELaNa XII mission as an auxiliary
records should be in the form of photographic evidence and thorough payload aboard the NROL-55 Mission
documentation. This is especially important for student organizations that on October 8, 2015. [University of
will be losing senior team members as they graduate. Keeping records helps Alaska, Fairbanks]
continuity within the project; you’ll avoid “reinventing the wheel” over and
over again.
There are two types of testing you will do for your CubeSat. The first type, devel-
opment testing, is internal testing you’ll do for your own purposes. The second
type, verification testing, you’ll do to prove to CSLI and the launch provider
that your CubeSat is safe and sturdy. You can do as much development testing
as you want, and no documentation will be due to CSLI. Once your CubeSat
build is complete, you will be required to perform specific testing and submit test
plans and reports to verify that the CubeSat meets the ICD requirements. After
verification testing is performed, you cannot work on the CubeSat any longer, electrical inhibit: An electrical
or you will be required to perform the verification testing again. Verification inhibit is a physical device that
testing typically includes vibration and thermal vacuum tests, and in some cases interrupts the “power path”
needed to turn on your CubeSat
shock, EMI/EMC, and static load tests, to ICD-prescribed levels. Day In The
and/or other potentially hazardous
Life (DITL) testing is also required to show that electrical inhibits and timers
devices.
will function correctly.
For vibration and shock testing, testing containers may be available for your
CubeSat. This testing container is a simplified version of the actual flight dis-
penser to act as a flight-like interface between your CubeSat and the testing appa-
ratus. Ask your mission integrator if there are testing versions of your assigned
dispenser available.
24 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
>>FREE ADVICE
DEVELOPMENT TESTING. “Test like you fly” is a common mantra for CubeSat
developers and applies to more than just final environmental testing.
During electronic development, use evaluation and development kits and
breadboard components before fabricating boards. Once the printed circuit breadboard: A breadboard
boards (PCBs) are produced, test as many expected functions as possible is a board used to make
before interfacing it with other systems. Keep the scope small with testing an experimental model of
and add components systematically, testing them along the way. Never components for testing.
assume that boards or subsystems that work well during standalone testing
will work well when integrated with other boards or subsystems.
During mechanical development, it is useful to do thermal and vibration tests
on individual subsystems prior to integrating all components. This often
catches design issues early on and reduces over-test on the overall system.
Testing should be completed with all documentation submitted to the mission
integrator no later than 1 month prior to the readiness reviews.
2.12 Mission Readiness Reviews (Half-Day)
The Mission Readiness Review (MRR) is a presentation that you
will deliver to CSLI and the mission integrator summarizing all
of the evidence you’ve provided to show that your CubeSat sat-
isfies all of the requirements in the ICD. All of your deliverable
documentation should be submitted to, and accepted by, the mis-
sion integrator prior to this review. That means all testing should
also have been completed, and your CubeSat should be com-
pletely finished. This review cannot be completed by telephone;
all CubeSat teams manifested on the mission are required to send
at least one representative to present at the readiness review—so
don’t forget to budget for travel! The location of the review will
be determined by LSP and the mission integrator. An MRR out-
SporeSat undergoing vibration testing. SporeSat is
line or template will be provided to each team by the mission
a space biology science mission designed by Ames
integrator at least 1 month prior to the review. Your team will be Research Center to gain a deeper knowledge of the
required to submit a draft of the presentation 2 weeks or more mechanism and determine the threshold of cell gravity
sensing. Launched by NASA’s CubeSat Launch Initiative
before the review. This MRR pre-check of your draft is for your
on the ELaNa V mission as an auxiliary payload aboard
benefit as well as the reviewers. The mission integrator will be able the SpaceX-3 Cargo Resupply Mission on April 18, 2014.
to catch a lot of errors and ensure all information is covered so the [NASA Ames Research Center]
actual MRR goes as smoothly as possible.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 25

CubeSat
101
CHAPTER 2 Development Process Overview
2.13 CubeSat-to-Dispenser Integration and Testing
(2 days)
It’s delivery day! You’ve completely finished your CubeSat—all testing is complete
and all paperwork has been submitted. Now you get to deliver your CubeSat to
the integration site, the location of which is determined by the mission inte-
grator. When you arrive at the integration site you’ll unpack your CubeSat and
move it into the integrator’s clean room. It’s not required, but the integrator may
request that you help with the integration process. This means being responsible
for positioning the CubeSat on the workbench while the integrator takes the pre-
integration physical measurements. Some integrators
will make a great effort to avoid handling the CubeSat.
You may even get to insert your CubeSat into the dis-
penser. In addition to integration activities, and assum-
ing the integration facility allows cameras, there may be
photo opportunities. These photos can be great publicity
for your program—and for your scrapbook—so don’t
forget to bring your pretty smiles! Once the dispenser
door is closed, and all photos are taken, your job is done.
The integrator will seal the dispenser and that typically
concludes day 1.
On day 2, the dispenser and CubeSat will go through
a final vibration test as a single unit to make sure inte-
gration was successful. And that’s it—the integrator will
take it from there.
The CSSWE (Colorado Student
Space Weather Experiment)
Generally, the developers are required to attend integration. This is to ensure that CubeSat and PPOD just prior to
integration. The CSSWE launched on
if any issues arise they can be addressed real time and it is also the last time you’ll
September 13, 2012 as an auxiliary
see your CubeSat. payload on the ELaNa VI mission
aboard the NROL-36. [University of
Colorado at Boulder]
After integration to the dispenser is complete, you won’t have access to the
CubeSat again. With prior approval, you may run system diagnostics or perform
battery charging at the integration site before the CubeSat is buttoned up in the
dispenser. However, in the event that there is a very long launch delay (e.g., if
your launch is delayed by several months) the developers may have an opportu-
nity to access their CubeSats again, but this is only in extreme circumstances and
is by no means guaranteed.
26 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
Any special accommodations (clean room, tem-
perature, humidity, security, storage, etc.) that
your CubeSat requires at the integration site
should be requested at the start of the mission.
Additionally, you will need to inform the inte-
grators about any Ground Support Equipment
(GSE) you plan to bring to the site, as well as
any potential hazards to integration personnel.
If the CubeSat has any possible hazards (e.g.,
laser emitters), the CubeSat team will need to
provide safety gear for the integration team
(e.g., protective eyewear).
After the CubeSat is integrated into the dis- Technicians integrating a PPOD
containing CubeSats onto the Delta
penser, the mission integrator will inspect the loaded dispenser one more time.
II launch vehicle as part of the ELaNa
Then the dispenser will be packaged and shipped to the integration site where the X mission that was launched as an
loaded dispenser will be integrated onto the launch vehicle. auxiliary payload on NASA’s Soil
Moisture Active Passive (SMAP)
Mission. [NASA]
2.14 D ispenser-to-Launch Vehicle Integration
(1 day)
Dispenser-to-launch vehicle integration is the point at which the dispenser loaded
with your CubeSat is attached to the rocket. This sounds pretty cool, and it is, but
unfortunately, you aren’t invited. The launch vehicle providers are very protective
of their rockets, so only essential personnel are permitted to participate. Essential
personnel usually include LSP representatives, the mission integrator, and the
launch provider’s technicians.
The process only takes about a half-day to a day, depending on the launch vehicle.
Not all missions are run the same way, but typically on the big day, the mission
integrator will arrive at the launch vehicle site with the loaded dispenser. The LV
technicians will lead the integrator to the location on the LV where the dispenser
is to be affixed. After a final cleaning and inspection, the mission integrator will
hand off the dispenser to the LV technicians. The technicians will follow a pre-
scribed procedure to carefully attach the dispenser to the LV. Finally, photo-
graphs will be taken as evidence that the integration was successful, and your
CubeSat will be that much closer to space.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 27

CubeSat
101
CHAPTER 2 Development Process Overview
The integration to the LV typically occurs 2 weeks to 4 months prior to launch.
It all depends on which LV your CubeSat is using. Each mission model is differ-
ent and explained in more detail in the Mission Models section (Chapter 3) of
this document.
2.15 Launch (1 day)
The launch location will depend on the pri-
mary mission, and will be known well before
the CubeSats are manifested. The launch
date may change from the original timeline,
but only the primary mission or launch vehi-
cle can move the launch date. The CubeSats
do not have any influence on the launch or
launch window. If your project gets delayed
for any reason, the launch will not be delayed.
If your CubeSat is not delivered in time,
the LV will definitely leave without your
CubeSat onboard.
While the CubeSat developers won’t have an
active role in launch operations, you will usu-
ally be invited to come to the launch site and Launch of ELaNa-II from Vandenberg
watch the LV take off. Travel will be at your own expense, but most teams think Air Force Base, CA on December 6,
2013. Four CubeSat Missions were
it’s well worth it. While you’re there, LSP may ask that you participate in some
deployed. [Corkery/ULA]
public affairs and outreach events (e.g., NASA EDGE interviews, photos, etc.).
Be aware that the launch date is subject to change at any time and day-of-launch
scrubs are common due to weather and other factors. So, if you plan to travel to
the launch, it may be wise to include some extra days in the event of a last-minute
launch delay.
28 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 2 Development Process Overview
2.16 Mission Operations (variable, up to 20 years)
Initial operations can be the most exciting part of a satellite mission, especially to
first-time flyers; however, it can also be the most challenging. But not to worry,
the mission integrator will work with your team to get communications up and
running after launch.
By now your team should have had plenty of practice using the ground station on
engineering and/or flight versions of your own CubeSat, as well as some practice
tracking existing CubeSats. You may have even been able to request permission
from other CubeSat teams to uplink to their satellites. Having operations experi-
ence during the development of your CubeSat is invaluable because it helps you
decide what commands will work best when your CubeSat is in orbit. Existing
satellites are a good starting point because the orbit and satellite behavior should
be well established.
>>FREE ADVICE
HOW TO TRACK A SATELLITE. To predict where any satellite is in orbit, two-
line element (TLE) sets are entered into satellite tracking software that two-line element (TLE): A
calculates the expected position of the satellite. TLEs can be generated from TLE is a data format encoding
various sources; however, the most widely available and accurate TLEs are a list of orbital elements of an
produced by the United States Air Force’s Joint Space Operations Center Earth-orbiting CubeSat for a given
(JSpOC) at Vandenberg Air Force Base in California. The JSpOC publishes point in time, the epoch. Using a
prediction formula, a TLE can be
TLEs for most of the satellites currently in orbit on its Web site, http://
used to estimate the position and
www.space-track.org. The JSpOC Web site is also a great place to review
velocity in the past, present or
satellite-tracking data, because their records go back to 1957, the beginning
future for your CubeSat.
of the space program.
0 CXBN-2
1 42704U 98067LM 17304.55488591 .00021073 00000-0 25707-3 0 9994
2 42704 51.6386 74.8642 0001580 42.1764 317.9350 15.60423680 26110
Directly following a launch, the first challenge is determining which new object
is your satellite. The launch provider usually provides preliminary state vectors
before the launch date so the CubeSat developers can plan and schedule their
operations. State Vectors specify the position and velocity of CubeSat relative to
the Earth’s center of mass and are used to predict viewing times and the position
of your CubeSat.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 29

CubeSat
101
CHAPTER 2 Development Process Overview
The University of Colorado at
Boulder Miniature X-ray Solar
Spectrometer (MinXSS) CubeSat
followed by the University of Michigan
CADRE CubeSat, are deployed from
the Space Station on May 16, 2016
on the ELaNa IX mission. The MinXSS
mission is a science investigation
to study solar flares, active regions,
the quiescent Sun, and their impact
on Earth’s upper atmosphere. The
CADRE mission is a space weather
investigation that will improve our
understanding of the dynamics of
the upper layers of our atmosphere:
the thermosphere and ionosphere.
[NASA]
Right after the CubeSats are ejected into orbit on launch day, the launch provider
will provide actual state vectors that can be converted into TLEs. It can take
some time—from a couple days up to a week or so—for the JSpOC to produce
rough TLEs. The accuracy of the TLEs will become more refined over the fol-
lowing few weeks. During this time, the mission integrator will be working both
with the JSpOC and the CubeSat teams to help determine which satellite belongs
to which TLE. Some CubeSats carry GPS receivers, which helps identify each
satellite by process of elimination. It’s not uncommon for it to take several weeks
to confidently identify all of the satellites from a launch.
If you’re planning to use a radio frequency in the amateur band (more fre-
quency band details in Chapter 5.1), you can get help contacting your satellite
from the amateur radio community. In the past, CubeSat developers have posted
announcements online to get help from volunteer satellite trackers. These volun-
teers have been very helpful identifying CubeSats. You can get more details by
reaching out to fellow CubeSat teams online and at conferences.
One more resource to help you out is the CubeSat Internet Relay Chat (IRC)
channel. During and directly following launch, most of the active amateur sat-
ellite-tracking enthusiasts meet on the CubeSat IRC channel to share observa-
tions and work to identify each CubeSat. Most “first contacts” occur on this IRC
channel, and many are from other parts of the world. To join the CubeSat IRC
channel, point your favorite IRC client to: irc.freenode.net #cubesat
30 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
3
Mission Models IN THIS CHAPTER
3.1 NASA-Procured Launch Vehicle
Mission Model
3.2 Operationally Responsive Space
(ORS) Rideshare Mission Model
3.3 National Reconnaissance Office
(NRO) Rideshare Mission Model
We know from Chapter 1 that CSLI has flown CubeSats on a number of
3.4 Commercial Launch Service
different launch vehicles, but did you know that those launch vehicles Through a Third-Party Broker
were sponsored by different organizations? In this chapter we want to tell you Mission Model
about the different types of missions that CSLI CubeSats have been a part of. 3.5 International Space Station (ISS)
Deployment Mission Model
These organizations have a particular way they like to run their missions. These
are called “mission models.” That means your CubeSat team will work with
requirements and organization structures specific to the type of mission your
CubeSat is manifested on. To better prepare your team for what you can expect,
Pictured above:
we’ll go over the major differences in the mission models (listed below) that CSLI
IceCube Team working at NASA’s
has worked with thus far.
Goddard Space Flight Center. The
objective of the IceCube mission is
1. NASA-Procured Launch Vehicle Mission Model to demonstrate the technology of
a sub-millimeter-wave radiometer
2. Operationally Responsive Space (ORS) Rideshare Mission Model for future cloud ice sensing. This
technology will enable cloud ice
3. National Reconnaissance Office (NRO) Rideshare Mission Model
measurements to be taken in the
intermediate altitudes (5 km–15 km),
4. Commercial Launch Service through a Third-Party Broker Mission Model
where no measurements currently
5. International Space Station (ISS) Deployment Mission Model exist. Launched by NASA’s CubeSat
Launch Initiative on the May 24, 2017
ELaNa XVII mission on the seventh
Orbital-ATK Cygnus Commercial
Resupply Services (OA-7) to the
Space Station. [NASA]
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 31

CubeSat
101
CHAPTER 3 Mission Models
3.1 NASA-Procured Launch Vehicle Mission Model
It’s no surprise that CSLI has placed CubeSats on launch vehicles being used
for NASA missions. This is known as the NASA-Procured Launch Vehicle mis-
sion model. Every year, NASA LSP procures launch vehicles for NASA and
other civil U.S. Government agencies that will conduct missions to further sci-
entific research or conduct technology demonstrations. When those missions’
requirements allow for it, CSLI CubeSats are allowed to hitch a ride to orbit.
The CubeSat requirements for these flights are based on LSP-REQ-317.01 and
the CubeSat Design Specification (CDS), both of which are discussed in the
range safety: Range safety is
Requirement Sources section (Chapter 4). the person designed to protect
people and assets on both
The organizational chart in FIGURE 10 outlines the organizations involved in the rocket launch range and
downrange in cases when a
NASA-Procured Launch Vehicle mission model. For CubeSat missions, NASA
launch vehicle might expose them
typically contracts mission coordination duties to an outside organization.
to danger.
Mission coordination duties can include the following: coordinating safety doc-
umentation with range safety, interfacing with the CubeSat developers, verify-
ing ICD requirements, acting as the point of contact for the FCC and NOAA,
performing CubeSat-to-dispenser integration and testing, and coordinating with
the JSpOC to identify each CubeSat in orbit. Finally—and here’s the part that
NASA Primary Mission
LV Provider
Primary Mission Representative
NASA LSP
Mission Management
CSLI Mission Integrator Launch of the ELaNa-X mission on
Mission Coordination, Dispenser January 31, 2015, as an auxiliary
Integration, and Acceptance Testing payload on NASA’s Soil Moisture
Active Passive (SMAP) mission
from Vandenberg Air Force Base,
Calif. Three CSLI CubeSats were
CSLI deployed: FIREBIRD II A,B from
CubeSats Montana State University, Bozeman,
Mont.; GRIFEX from the Jet
Propulsion Laboratory, Pasadena,
FIGURE 10: NASA-Procured Launch Vehicle Mission Model Organizational Chart Calif.; and EXOCUBE from Cal Poly,
San Louis Obispo, Calif. [NASA]
32 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 3 Mission Models
A Minotaur I rocket carrying, among
other payloads, 11 small CubeSat
research satellites as part of NASA’s
fourth ELaNa mission, lifts off from
Virginia’s Mid-Atlantic Regional
Spaceport Pad 0B at NASA’s
Wallops Flight Facility at 8:15 p.m.
EST Nov. 19, 2013. This launch
marked the launch of the first high-
school-built cubesat, TJ3Sat built
by Thomas Jefferson High School,
Alexandria, VA. [NASA/Ali Stancil]
affects your team—the mission integrator and/or NASA typically requires regu-
lar mission tag-ups via telephone with the CubeSat developers. During these tag-
ups the mission integrator will update the team on mission status and ask each
developer to provide an update on their CubeSat status. You, as the developer,
are expected to keep the mission integrator and NASA informed of your develop-
ment status and any issues that might crop up.
All of your deliverables will be submitted to and reviewed by the mission inte-
grator and approved by NASA LSP. The mission integrator is responsible for rec-
ommending to NASA LSP whether or not each CubeSat team is ready for flight.
NASA will be responsible for ensuring that all CSLI CubeSats comply with
NASA orbital debris mitigation requirements and will generate the Orbital
Debris Assessment Report (see Chapter 6.1) for all CSLI CubeSats.
In addition to the documentation, NASA also requires each team to present a
readiness review in person to the mission integrator with NASA LSP as an advi-
sor. This is the same readiness review we discussed in the Development Process
Overview section (Chapter 2.12).
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 33

CHAPTER 3 Mission Models
3.2 Operationally Responsive Space (ORS)
Rideshare Mission Model
The Operational Responsive Space (ORS) Office isn’t as well known as NASA,
but they’ve been very supportive of CubeSat missions. It’s a joint effort of mul-
tiple agencies within the U.S. Department of Defense (DOD), and they have
provided space on their launch vehicles to CubeSats in need of a ride to orbit.
ORS launches have given rides to CSLI CubeSats as well as to other non–CSLI
sponsored CubeSats.
The organizational chart in FIGURE 11 outlines the ORS Rideshare Mission Model.
ORS will contract with a mission integrator to oversee the development and inte-
gration of the LV and payloads on the mission. As with the NASA mission model,
these responsibilities may include coordinating safety documentation with range
safety, interfacing with the CubeSat developers, verifying ICD requirements, act-
ing as point of contact for the secondary missions with the FCC and NOAA,
coordinating with the JSpOC for pre- and post-launch identification of objects,
and managing the physical CubeSat-to-dispenser integration.
In addition to the ORS mission integrator, there typically will be another mission
integrator contracted by ORS to deal specifically with the CSLI CubeSat teams.
ORS Office
ORS Mission Integrator LV Provider
NASA LSP
Mission Management
CSLI Mission
Integrator
CSLI ORS
CubeSats CubeSats
FIGURE 11: ORS Rideshare Mission Model Organizational Chart
34 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CHAPTER 3 Mission Models
The CSLI mission integrator will have scaled-back responsibilities compared to
the equivalent role in the NASA-owned mission model, because the ORS mission
integrator is responsible for a number of the tasks. The CSLI mission integrator
will be limited to tasks related to tracking CubeSat development, performing ICD
verification tasks, and providing relevant updates to the ORS mission integrator.
This person will also participate in the ORS Mission tag-up meetings with ORS,
and will speak on behalf of the CubeSat teams. The CSLI mission integrator will
hold separate tag-ups for the CSLI CubeSats. Each CubeSat team will present a
readiness review to the CSLI mission integrator and the ORS mission integrator
with NASA LSP acting as an advisor. As with all mission models, CSLI CubeSat
teams will be required to present in-person for their readiness review.
Kathryn Clements and Mary Distler,
You, as the CubeSat developer will submit all of your document deliverables to
students at St. Louis University, with
the CSLI mission integrator. So, from your point of view, everything is pretty the Argus CubeSat after completing
much the same on an ORS mission as it is on a NASA mission: a member of pre-integration checkout. Launched by
NASA’s CubeSat Launch Initiative on
your CubeSat team will have regular tag-up meetings with a mission integrator,
the ELaNa VII mission as an auxiliary
submit all required documentation to an integrator, and participate in a readiness payload aboard the U.S. Air Force-led
Operationally Responsive Space (ORS-
review for final launch approval.
4) Mission on November 3, 2015. [St.
Louis University]
NASA will be responsible for ensuring that all CSLI CubeSats comply with
NASA orbital debris mitigation requirements and will generate the Orbital
Debris Assessment Report (see Chapter 6.1) for all CSLI CubeSats.
3.3 National Reconnaissance Office (NRO)
Rideshare Mission Model
DID YOU KNOW?
The NRO has been a great supporter of CubeSat technologies and has flown a
The NRO
number of CubeSats as auxiliary payloads on their launch vehicles. CSLI has
The National Reconnaissance
worked with the NRO for many years, and if your CubeSat mission is selected
Office (NRO) is an agency within
by CSLI to fly on a NRO mission, you will work primarily with the Auxiliary the United States intelligence
Payload Integration Contractor (APIC) team, which can be made up of multiple community. The NRO is responsible
for designing, building, and operating
organizations and is contracted by the NRO.
the reconnaissance satellites for the
United States Government. Although
The chart in FIGURE 12 shows all of the organizations involved in preparing
the NRO was established in 1961,
CubeSats for flight on NRO-sponsored launches. The Office of Space Launch
its existence wasn’t declassified
(OSL), located at the top of the chart, is the organization within the NRO that until 1992. If you’d like to know more
deals with launching satellites, as opposed to designing or operating them. about what the NRO does, their Web
site, http://www.nro.gov, is a great
place to start.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 35

CHAPTER 3 Mission Models
OSL
Office of Space Launch
LV Provider
(Under the National
Reconnaissance Office)
APIC
Auxiliary Payload Integration Contractor
Mission Integration
NASA LSP
Mission Management
CSLI NRO
CubeSats CubeSats
FIGURE 12: NRO Mission Model Organizational Chart
The APIC will be responsible for the mission integrator’s duties and will report
regularly to the launch vehicle provider and OSL. For these reports and any
readiness reviews to OSL, the APIC will need information and reports from the
CubeSat teams; however, the CubeSat teams won’t need to participate in any
of these meetings. Instead, the CubeSat teams will meet with the APIC team
separately, typically in biweekly tag-ups via teleconference. At these tag-ups, the
teams will provide status updates and alert the APIC to any issues that may affect
the schedule or their ability to meet requirements.
This is the launch of ELaNa-XII on
October 8, 2015, as an auxiliary
CubeSat teams will also be responsible for presenting a readiness review to the payload on the NROL-55 mission from
Vandenberg Air Force Base, Calif. Four
APIC, just like the other mission models. CSLI CubeSats will be required to
CubeSat missions were deployed:
present the review in-person to the APIC team, NASA LSP, and OSL.
BisonSat from Salish Kootenai College,
Pablo, Mont.; Fox-1 from AMSAT, The
NASA will be responsible for ensuring that all CSLI CubeSats comply with Radio Amateur Satellite Corporation,
Kensington, Md.; ARC-1 from the
NASA orbital debris mitigation requirements and will generate the Orbital
University of Alaska Fairbanks, Alaska;
Debris Assessment Report (see Chapter 6.1) for all CSLI CubeSats. and LMRSTSat from the Jet Propulsion
Laboratory, Pasadena, Calif. [ULA]
All deliverables submitted by the CubeSat teams will be reviewed by the APIC.
So, again, there isn’t much of a change for what your CubeSat team will need to
do compared to the other mission models we’ve talked about so far: a member
of your team will attend regular tag-up meetings with the APIC (the mission
integrator), submit all required documentation to the APIC, and participate in a
readiness review for final launch approval.
36 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 3 Mission Models
3.4 Commercial Launch Service Through a
Third-Party Broker Mission Model
CubeSat developers can purchase launches through third-party brokers on
non-Government launches, usually on commercial or foreign missions. CSLI can
also procure rides through a broker for payloads on commercial missions.
The requirements for these missions will come from
the LV provider via the broker (see FIGURE 13). NASA
LSP will not verify the CubeSat requirements; instead,
the broker will either serve as mission integrator or
assign one. The mission integrator will work with the
CubeSat and launch vehicle representatives to cre-
ate the CubeSat-to-dispenser ICD and determine
the appropriate schedule for document and hardware
deliverables. The mission integrator role for third-party
broker missions will be similar to that of the NASA
missions. The mission integrator for these missions may
not require readiness reviews, but may instead track the
status of document and hardware deliverables to verify
that the CubeSats are ready for flight.
NASA will be responsible for ensuring that all CSLI CubeSats comply with During an event Oct. 14, 2015, at the
Agency’s Kennedy Space Center
NASA orbital debris mitigation requirements and will generate the Orbital
in Florida, Garrett Skrobot, lead
Debris Assessment Report (see Chapter 6.1) for all CSLI CubeSats. for the ELaNa missions for NASA’s
Launch Services Program, shows
the size of the CubeSats that will be
launched under NASA’s contract
award for the Venture Class Launch
Third-Party Broker Services. Rocket Lab USA and Virgin
LV Provider
Mission Manager Galactic were awarded contracts
under the Venture Class Launch
Services competition to send several
CubeSats into space on flight profiles
CSLI
tailored to the needs of the CubeSats
CubeSats
manifested on each launch. [NASA/
Kim Shiflett]
FIGURE 13: Third-Party Broker Mission Model Organizational Chart
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 37

CubeSat
101
CHAPTER 3 Mission Models
3.5 International Space Station (ISS)
Deployment Mission Model
In addition to riding as auxiliary payloads mounted directly to launch vehicles,
CubeSats can also be deployed from the Space Station (see FIGURE 14). For this
type of mission, the CubeSats are integrated into dispensers on the ground, trans-
ported to the ISS in a pressurized cargo vessel (e.g., SpaceX Dragon, Orbital ATK’s
Cygnus, etc.), and hand carried onto the ISS from the cargo vessel. Astronauts
aboard the ISS are responsible for deploying the CubeSats from the ISS typically
1–3 months after arrival.
CubeSat mechanical and electrical requirements for ISS deployment are similar
to those found in the CDS. For a list of requirements specific to ISS deploy-
ment, please visit the NanoRacks Web site at http://nanoracks.com. NanoRacks
is currently the only commercial organization that can deploy CubeSats from
the ISS. Any CubeSat using their services will need to comply with the current
NanoRacks ICD. As with the other mission models, the CubeSats will submit
flight safety review documents to the mission integrator, and the mission integra-
tor will handle any reviews required by the ISS team.
NASA will be responsible for ensuring that all CSLI CubeSats comply with
NASA orbital debris mitigation requirements and will generate the Orbital
Debris Assessment Report (see Chapter 6.1) for all CSLI CubeSats.
NASA ISS LV Provider
Mission Integrator
Mission Coordination,
ISS Integration, and
Acceptance Testing
NASA LSP
Mission Management
CSLI Other
CubeSats CubeSats
FIGURE 14: ISS Mission Model Organizational Chart
38 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CCuubbeeSSaatt
110011
4
Requirement IN THIS CHAPTER
4.1 Mission-Specific Interface Control
Sources for Launch
Documents (ICDs)
4.2 Launch Services Program (LSP)—
Program-Level Requirements
4.3 CubeSat Design Specifications
(CDS)
4.4 Dispenser Standards/
Specifications
Unfortunately, you can’t know all of the requirements your CubeSat will 4.5 Federal Statutes
need to adhere to before you start your design process. The requirements 4.6 Range Safety Requirements
for previous CubeSat launches have all been similar, but they do vary with every
mission. You can, however, use some of the public documents that are discussed
in this chapter as guidelines. The CubeSat-to-dispenser ICD (provided by the
mission integrator after you’ve been manifested) lists your official requirements
and is derived from these public documents and the dispenser-to-LV ICD, which Pictured above:
St. Thomas More Cathedral
is specific to your LV. You can use the information in documents like LSP-
School STMSat-1 (1U) and
REQ-317.01, GSFC-STD-7000, and the CDS to help you get started, but your Nodes 1 and 2 (1.5U each)
final CubeSat design will need to meet all of the requirements in the mission deployment from the International
Space Station on May 16, 2016.
ICD provided to you by the mission integrator.
[NASA]
This chapter describes the documents involved in building your CubeSat’s set
of requirements. It’s important for you as the developer to understand what
these documents are and how they work together to form the requirements your
CubeSat will need to meet to be certified for launch.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 39

CubeSat
101
CCHHAAPPTTEERR 44 RReeqquuiirreemmeenntt SSoouurrcceess ffoorr LLaauunncchh
4.1 Mission-Specific Interface Control Documents
(ICDs)
As stated earlier, the mission-specific ICDs form the rulebook for your Cubesat.
That is because these documents explicitly and officially state what your CubeSat’s
requirements are for your particular launch. If your CubeSat fails to meet any of
these requirements, your CubeSat may not get to fly.
CubeSat missions generally have two ICDs, one to regulate the CubeSat-to-
dispenser interfaces, and one to regulate the dispenser-to-launch vehicle inter-
faces. The mission-specific CubeSat-to-dispenser ICD is usually generated and
maintained by the mission integrator. It captures all of the requirements from all
sources and typically includes the requirements from the dispenser-to-LV ICD,
the CDS, range safety requirements, and any other applicable documents. The
CubeSat-to-dispenser ICD will specify all of the environmental levels for which
you will need to test your CubeSat. That includes, but is not limited to, vibration,
shock, thermal vacuum, and acoustic environments.
4.2 Launch Services Program (LSP)—
Program-Level Requirements
Before your mission ICD is available, you, as a CubeSat developer, will want to base NASA LSP’s most recent revision
of the Program Level Requirements
your preliminary designs on the requirements in NASA LSP’s most recent revision
LSP-REQ-317.0 Document. [NASA]
of the Program Level Requirements (LSP-REQ-317.01). This set of requirements
was developed specifically for CubeSats and dispensers integrated on NASA Primary
Payload Missions where LSP has procured the launch vehicle (see the NASA-
Procured Launch Vehicle Mission Model in Section 3.1. The purpose of these par-
ticular requirements is to ensure that the CubeSats and dispensers will contribute no
added risk to the primary payload. These requirements will be incorporated into the
mission ICDs. The latest revision of LSP-REQ-317.01 can be found on the NASA
Web site (https://www.nasa.gov/pdf/627972main_LSP-REQ-317_01A.pdf).
4.3 CubeSat Design Specifications (CDS)
The CDS is a set of general requirements used to define a standard CubeSat.
Developers can use the CDS in the preliminary design phase, but keep in mind
that this is not the official set of requirements that your CubeSat will need to
CubeSat Design Specifications
meet. The most recent version can be found at http://www.cubesat.org.
Document [Cal Poly]
40 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 44 RReeqquuiirreemmeenntt SSoouurrcceess ffoorr LLaauunncchh
4.4 Dispenser Standards/Specifications
All CubeSat dispenser models on the market will accommodate a CubeSat
designed to the requirements in the CDS, but each offers its own particular set of
options. Before beginning the design process for your CubeSat, it would behoove
you to research the differences between available dispensers. If you’re already
familiar with each dispenser, you’ll be in a better position to make adjustments
to your design when CSLI matches your CubeSat with a launch and specifies the
dispenser that will be used. The specifications for each dispenser are located on
their respective Web sites.
4.5 Federal Statutes
There are Federal laws regulating the use of CubeSats. Some are more
obscure than others, but the most significant laws deal with radio fre-
quency (RF) transmissions, orbital debris, re-entry risk, and Earth
observation.
The Federal Communications Commission (FCC) is responsible for
regulating all radio transmissions generated by non-Government U.S.
entities, including CubeSat communications. The official document
that specifies the FCC rules for CubeSats is in the Code of Federal
Regulations (CFR). The specific chapter is 47 CFR Part 97, but if you’d
like a more practical discussion of the licensing process, your team can
refer to the Licensing Procedures chapter (Chapter 5) of this document.
The National Oceanic and Atmospheric Administration (NOAA)
is the regulatory agency overseeing the remote sensing capabilities of
non-Government orbiting spacecraft, including CubeSats. By “remote
sensing,” we mean any sort of sensing capability, like picture taking or
imaging, that your CubeSat might have. NOAA is tasked with licensing
all spacecraft that have remote sensing capabilities that could possibly
John Kolasinski (left), Ted Kostiuk
catch an image of Earth. If you have a sensor that could possibly glimpse
(center), and Tilak Hewagama
Earth, you must contact NOAA in order to know if your CubeSat requires a
(right) hold mirrors made of carbon
remote sensing license. NOAA is the sole determining authority of the need for nanotubes in an epoxy resin. The
mirror is being tested for potential use
a license. Operators and owners should always assume a license is needed. The
in a lightweight telescope specifically
Code of Federal Regulations at 15 CFR Part 960 covers the rules regarding this for CubeSat scientific investigations.
licensing process. [NASA/W. Hrybyk]
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 41

CubeSat
101
CCHHAAPPTTEERR 44 RReeqquuiirreemmeenntt SSoouurrcceess ffoorr LLaauunncchh
4.6 Range Safety Requirements
Anyone launching anything from a U.S. launch site must adhere to safety require-
ments intended to protect people and property on/in the surrounding land, sea
and air. In the U.S., there are Government launch sites and commercial launch
sites. Launches from U.S. Government launch sites within the Eastern (Kennedy
Space Center and Cape Canaveral Air Force Station) or Western (Vandenberg
Air Force Base) Ranges, must adhere to very particular safety requirements.
These requirements can be found in the Air Force Space Command Manual
(AFSPCMAN 91-710), the Air Force Occupational Safety and Health Standards
(AFOSHSTD 48-9), and the Eastern Western Range Safety Requirements (EWR
127-1). If by chance you are launching from Wallops their Range Safety Manual
for Goddard Space Flight Center (GSFC) and Wallops Flight Facility (WFF) will
be used. Many of the requirements of these documents are encompassed in the
CubeSat-to-dispenser ICD.
Student Bungo Shiotani from the
University of Florida, Gainesville,
working on the SwampSat CubeSat
mission to demonstrate precision
three-axis attitude control in orbit
using a pyramidal configuration of
control moment gyroscopes (CMG).
The CubeSat was launched by
NASA’s CubeSat Launch Initiative
on the ELaNa IV mission as an
auxiliary payload aboard the U.S. Air
Force-led Operationally Responsive
Space (ORS-3) Mission on November
19, 2013. [University of Florida,
Gainesville]
42 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
5
Licensing
IN THIS CHAPTER
Procedures 5.1 Radio Frequency (RF) Licensing
5.2 Remote Sensing
We’ve explained the importance of obtaining proper licensing for your Pictured above:
University of Kentucky students Jason
CubeSat. This chapter will help you determine which licenses to pursue
Rexroat and Alex Clements working on
and how to get them. Like we’ve stated before, any CubeSat that can transmit RF KySat-2 a technology demonstration
or take images and that is owned or operated by a U.S.-based organization will CubeSat mission developed by students
from the University of Kentucky in
be required to obtain specific licenses and/or authorizations. For non–U.S.-based
Lexington, Kentucky that builds
organizations, licensing of RF operations will be required by the organization’s upon KySat-1 by expanding the K-12
outreach goals to interest students to
national regulatory authority.
science, technology, engineering and
mathematics (STEM) fields and space
As you develop your CubeSat, you should check the source references pro-
technology. It also will test components
vided in each chapter to verify that you are following the current proce- of a novel attitude determination
system called a Stellar Gyroscope that
dures and requirements. The rules and requirements change over time, and
uses sequences of digital pictures
you will need make sure you are up-to-date so that your licensing process goes as to determine the three-axis rotation
smoothly as possible. rate of the satellite. Launched by
NASA’s CubeSat Launch Initiative on
the ELaNa IV mission as an auxiliary
payload aboard the U.S. Air Force-
5.1 Radio Frequency (RF) Licensing
led Operationally Responsive Space
(ORS-3) Mission on November 19, 2013.
[University of Kentucky]
CubeSat licenses have different classifications depending on who the primary
operator of the CubeSat will be and how it is to be used. Each classification has
its own set of requirements and procedures. In this chapter, we’ll help you under-
stand the differences between the types of licenses and which will be appropriate
for your CubeSat mission.
While it’s not critical for you to know everything that goes on behind the cur-
tain, you may want to have an idea of how your paperwork is being processed.
You can find information online about CubeSat licensing. There are a number of
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 43

CubeSat
101
CHAPTER 5 Licensing Procedures
Web sites run by amateur operators, other devel-
opers, and Government agencies (FCC, NASA
Spectrum, etc.) that break down the licensing
process in greater detail. More comprehensive
information can be found in FCC1 and NASA
Spectrum2 guidance documents.
Prior to finalizing any design, operations plans or
submitting license requests, you should under-
stand the core regulatory rules including techni-
cal constraints that are in place to enable sharing
between systems in certain frequency bands. You
do not want to design and build a system that vio-
lates regulatory rules since during the licensing
process you may not be able to correct any issues
found. Projects may want to consult with orga-
nizations or individuals familiar with spectrum
regulations during the design phase to ensure
compliance. Depending on the type of mission, the mission integrator may also Students from the University
of Michigan holding The
help your team obtain the RF license for your CubeSat.
Geostationary Coastal and Air
Pollution Events (GEO-CAPE)
Read-Out Integrated Circuit
License Types (ROIC) In-Flight Performance
Experiment (GRIFEX) 3U CubeSat
• Amateur: Designed specifically for amateur radio enthusiasts and to mission developed by the Jet
Propulsion Laboratory and students
serve the amateur radio community.
from the University of Michigan who
• Commercial: For commercial use, not applicable for non-commercial will perform engineering assessment
of a JPL-developed, all digital, in-pixel
university-based CubeSats or CSLI selectees. high frame rate ROIC. Launched by
NASA’s CubeSat Launch Initiative on
• Experimental: For radio frequency emitting systems on spacecraft con-
the ELaNa X as an auxiliary payload
taining experiments. Typical license for university CubeSats or CSLI aboard the Soil Moisture Active
selectees. Passive (SMAP) Mission on January
31, 2015. [University of Michigan]
• Government: For spacecraft that operate radio frequency systems that
“belong to and are operated by” any U.S. Government agency.
1 FCC Guidance on Obtaining Licenses for Small Satellites (DA: 13-445) (http://
www.fcc.gov/document/guidance-obtaining-licenses-small-satellites)
2 Spectrum Guidance for NASA Small Satellite Missions (https://www.nasa.gov/
directorates/heo/scan/spectrum/policy_and_guidance.html)
44 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 5 Licensing Procedures
Amateur—FCC Part 97
This is the simplest case, but the most difficult to qualify for; very few CubeSats
qualify for purely amateur designation. This designation is intended for satellites
that will be used by amateur operators only. There can be no Government or
commercial involvement in the development or operation of the CubeSat. So, if
your CubeSat project is being funded by a Government grant, you are disqual-
ified from getting an amateur designation. It’s important to note that, when
determining amateur status, the FCC focuses on who the operator is, and
NOAA focuses on who the owner of the CubeSat is.
Amateur satellites are typically used to help operators to self-train and perform
intercommunication and technical investigations. The satellite operates within
a range of frequency bands that are allocated to the Amateur-Satellite Service,
which have been set aside for radio operators with purely noncommercial pur-
poses. One group that consistently develops amateur CubeSats is the Radio
Amateur Satellite Corporation (AMSAT). They’re a largely volunteer group inter-
ested in advancing space education, science, and technology. If you’re interested
in learning what an amateur class CubeSat project looks like, you can visit their
Web site, http://www.amsat.org/. The AMSAT Fox-1 CubeSat primary
focus was education and it hosted a
communications package specifically
A satellite with an amateur license isn’t limited to transmitting over the United
designed to be easy-to-use, requiring
States; this means that the satellite can communicate with ground stations located only a simple walkie-talkie–style
radio combined with a small hand-
anywhere in the world. The transmissions cannot be encrypted in any way and
held antenna. Using amateur radio
must consist of open information (i.e., nothing that’s supposed to be a secret or frequencies, it was open and
proprietary). The eligibility rules are listed in 47 CFR Part 97. available to the general public. Fox-1
was launched by NASA’s CubeSat
Launch Initiative on the ELaNa XII
Unlike other licenses, an amateur satellite license is not a stand-alone license, but
mission as an auxiliary payload
an addition to the radio operator’s existing amateur license. Although the opera- aboard the NROL-55 Mission on
October 8, 2015. [AMSAT]
tor does not have to obtain a new license, and there is less paperwork to complete,
it is not a trivial process. Any person who will be operating an amateur satellite is
required to have an amateur operator license. Information on how to obtain this
license for your team members can be found on the FCC’s Web site.
Any amateur (or experimental-licensed) spacecraft that use frequency bands allo-
cated to the Amateur-Satellite Service must coordinate with the International
Amateur Radio Union (IARU). Immediately after the CubeSat is manifested, if
not earlier, a frequency coordination request should be sent to the IARU to ask for
a frequency assignment for the CubeSat transmitter. Information can be found
on the IARU Web site at http://www.iaru.org/satellite.html. Because the IARU
is made up of volunteers across the world, they only meet periodically to review
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 45

CubeSat
101
CHAPTER 5 Licensing Procedures
applications. This means each review cycle can take a significant amount of time.
Thus, it is strongly suggested that you have someone with previous experience
working with the IARU to review your application before you submit it, in order
to reduce the likelihood of your application being kicked back for corrections.
IARU will respond to your frequency coordination request with a coordination
letter that will identify the frequency to which your CubeSat has been assigned.
As soon as you have your frequency assignment letter from IARU, you will be
able to assemble the FCC documentation. The licensed amateur operator will
need to submit what’s referred to as a prelaunch notification no later than 30 days
after being manifested. If there’s only a short timeframe between manifest and
integration to the launch vehicle, then the prelaunch notification must also be
submitted (no later than 90 days before integration).
DID YOU KNOW?
What’s the IARU?
The International Amateur Radio Union (IARU) is an international agency run by
volunteers who are based in countries around the world, who coordinate what
group will be allowed to use which radio frequencies in the amateur band. As
you can imagine, lots of people are transmitting for various reasons all day,
everyday. To avoid transmissions interfering with each other by using the same
frequency, IARU keeps track of which amateur frequencies are available and
assigns the unused bands upon request. That’s why the FCC requires CubeSat
developers to contact the IARU for an amateur frequency assignment before an
RF license can be processed.
For an amateur license, the FCC will need the following:
SpaceCap notice: The Space
• IARU coordination letter notification system PC Capture,
• Satellite orbital debris mitigation compliance document (discussed in or SpaceCap, is a software file
Chapter 6) containing information about
• SpaceCap notice: the SpaceCap software can be downloaded from transmitting stations in space,
http://www.itu.int) including details about antennas,
• Prelaunch notification letter with general mission and satellite information transmitters, and the station itself.
The file is created by PC-based
software that can be downloaded
Note: The FCC won’t request your SpaceCap file until after the initial applica-
for free from the International
tion submission. Telecommunications Union (ITU)
Web site.
On certain types of missions, the above information is e-mailed by the
mission integrator to the FCC International Bureau and copied to
amsat.spacecap@fcc.gov.
46 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 5 Licensing Procedures
Experimental—FCC Part 5
Although very few CubeSats qualify as purely amateur
radio stations, non-Federal CubeSats that involve radio
frequency use “for the purposes of experimentation, prod-
uct development, and market trials,” not commercial oper-
ations, may seek licensing under the FCC experimental
licensing rules (Part 5). Most university or nonprofit orga-
nization based systems, such as those supported by NASA’s
CubeSat Launch Initiative, qualify for FCC experimental
licensing.
The process for submitting an experimental license applica-
tion depends on the duration of the mission.
• Special Temporary Authority (STA) Form
should be used for experiments lasting less
than six months. The STA application form is
online: https://apps.fcc.gov/oetcf/els/forms/
STANotificationPage.cfm
• Form 422 should be used for experiments last-
ing longer than six months. The process for sub-
mitting an application for FCC experimental
licensing is described online at https://apps.fcc.
gov/oetcf/els/forms/442Entry.cfm.
Experimental licenses are not limited to a particular frequency band; however, The BisonSat mission is an Earth
Science mission that will demonstrate
CubeSats using frequency bands allocated to the Federal Government on an
the acquisition of 100-meter or
exclusive or shared basis are required to coordinate with U.S. Federal agencies.
better resolution visible light imagery
The FCC will initiate this coordination as part of the application process; how- of Earth using passive magnetic
stabilization from a CubeSat.
ever, projects are highly encouraged to seek guidance prior to developing any
BisonSat is the first CubeSat
systems in such bands. Careful attention must be made since special circum- designed, built, tested, and operated
stances may apply. In addition, CubeSats using frequency bands allocated to the by tribal college students. Launched
by NASA’s CubeSat Launch Initiative
Amateur-Satellite Service must coordinate with the IARU (see Amateur section
on the ELaNa XII mission as an
about IARU coordination). auxiliary payload aboard the NROL-
55 Mission on October 8, 2015.
[Salish Kootenai College]
CubeSats must also comply with technical constraints as specified by FCC reg-
ulations. Experimentally licensed CubeSats must operate on a non-interfer-
ence basis neither causing interference to or claiming interference from fully
licensed systems. To address any possible interference, FCC regulations require
that all CubeSats have the capacity to cease emissions. To enable sharing in some
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 47

CubeSat
101
CHAPTER 5 Licensing Procedures
bands, CubeSats may also need to limit emissions below certain power levels.
These are just a couple of the types of constraints that projects need to consider
in the design and operations of radio frequency systems.
Cubesat developers are responsible for gathering all necessary information
required for licensing prior to submitting a license request—delays in licensing
are often due to incomplete data.
For an experimental license, the FCC will need the following:
Form 442 or STA form: containing directed questions concerning gen-
eral mission, satellite and radio frequency equipment information;
additional information may also be needed;
EXHIBIT: If a Government contract is involved, a narrative state-
ment describing the contract circumstances
EXHIBIT: Research project and/or experimental purpose description
including detailed information about communication facilities
and operations (e.g., ground support)
Satellite orbital debris mitigation compliance document (discussed in
Chapter 6)
IARU coordination letter: for systems using Amateur-Satellite Service
bands
International Telecommunication Union (ITU) Cost Recovery letter:
projects are responsible for paying the fees for international coordina-
tion filings
Fee-exempt status letter (if applicable)
NOAA Remote Sensing license: or letter indicated that such licensing
is not needed
SpaceCap notice: the SpaceCap software can be downloaded from
http://www.itu.int.
Note: The FCC won’t request your SpaceCap file until after the initial application
submission.
48 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 5 Licensing Procedures
Chuck Clagett, Larry Kepko, and
Michael Johnson were instrumental in
developing the Dellingr 6U CubeSat
shown here inside NASA’s Goddard
Space Flight Center magnetic
calibration facility. Dellingr was
manifested on the ELaNa 22 mission
that launched on the SpaceX-12 on
August 14, 2017. [NASA/W. Hrybyk]
As with the other types of licenses, the application process for an experimental
license needs to start as soon as possible—preferably within 30 days after your
CubeSat is manifested or earlier. The FCC requires a minimum of 90 days from
the receipt of your application to issue a license, therefore complete FCC applica-
tions should be submitted in a timely manner.
Before your application can be submitted, CubeSats using frequency bands allo-
cated to the Amateur-Satellite Service must send an experimental coordination
request to the IARU asking for a frequency assignment for the CubeSat trans-
mitter. This should be done immediately after the CubeSat is manifested, if not
ear lier. That is because the IARU is made up of volunteers from across the world
and they only meet periodically to review applications. This means each review
cycle can take a significant amount of time. Thus, it is strongly suggested that you
submit your request early and have someone with previous experience working
with the IARU to review your application before you submit it, in order to reduce
the likelihood of your application being kicked back for corrections. When your
application has been approved, the IARU will then send you a coordination letter
identifying which frequency the satellite has been assigned.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 49

CubeSat
101
CHAPTER 5 Licensing Procedures
Once you receive the assignment letter, you will be able to begin assembly of
the application packet for the FCC. The process for submitting an application
for experimental licenses is very similar to the process for applying for an ama-
teur license, but instead of a prelaunch notification, you will need to submit
FCC Form 442 online or if your mission is expected to operate for less than 6
months, a Special Temporary Authority (STA) form can be submitted instead.
The appended documents are the same, but the STA application requires less
information from the applicant.
The FCC requires a minimum of 90 days from the receipt of your applica-
tion to license issuance, therefore—and this can’t be stressed enough—FCC
applications should be submitted ASAP.
Complete, detailed information is necessary otherwise license requests will bring
about lengthy queries seeking additional information. Early, but incomplete
license submissions do not confer any benefits. All required data for licensing
should have been gathered and reviewed during the requirements, design, and
review phases, so there is no reason not to have a complete application prior to
the time needed to file. CXBN, the Cosmic X-Ray
Background NanoSat was
Commercial Satellite—FCC Part 25 developed and built by students
from Morehead State University
Satellite operations for commercial purposes must obtain licensing through FCC
in Kentucky. Its primary purpose
Part 25 processes. This document does not address such commercial systems. is to increase the precision of
measurements of the Cosmic X-Ray
Background in the 30–50 KeV range.
Note: U.S. Government entities are prohibited from using FCC licenses for Launched by NASA’s CubeSat
Launch Initiative on the ELaNa VI
CubeSat operation.
mission as an auxiliary payload
aboard the NROL-36 Mission on
Government
November 13, 2012. [Morehead
The process for obtaining a Federal Government CubeSat certification and autho- State University]
rization is different from the process for securing FCC licensing. The NTIA is the
governing agency for Federal Government satellites (i.e., satellites that “belong to
and operated” by a Federal agency), so there is no need to submit an FCC appli-
cation. The frequency authorization process is well defined by the NTIA Manual
of Regulations and Procedures for Federal Radio Frequency Management (available
online on the NTIA Web site3). Your CubeSat’s team will work directly with the
appropriate Federal agency Spectrum Management Office to pursue system spec-
trum certification and frequency authorization. For example, NASA CubeSat
3 https://www.ntia.doc.gov/page/2011/manual-regulations-and-procedures-
federal-radio-frequency-management-redbook
50 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CHAPTER 5 Licensing Procedures
teams would work with their NASA Center’s Spectrum Office. The mission inte-
grator will have little to do with this type of licensing process, aside from regu-
larly bugging you about the status. For missions designated as NASA (Federal),
detailed information about the process can be found in the NASA/Spectrum4
guidance document.
5.2 Remote Sensing
Not all CubeSats will need a remote sensing license from NOAA, but if you
have a non–Federal Government CubeSat with any type of active or passive
imager, you must obtain a remote sensing license from NOAA’s Commercial
Remote Sensing Regulatory Affairs (CRSRA). While the mission integra-
tor will help with the RF licensing process on some types of missions, CubeSat
developers are solely responsible for obtaining the remote sensing license from
NOAA CRSRA.
You should start the process of applying for a remote sensing license by filling
out the one-page Initial Contact Form, found on the NOAA CRSRA Web site at
http://www.nesdis.noaa.gov/CRSRA. After NOAA has reviewed the form, they
will determine if your sensors require a license. If a license is required, they will
contact you for further information. Once NOAA has made their determination
either way, they will notify your team by letter or e-mail.
If a license is required, your team must send a written application to the Assistant
Administrator, NOAA Satellite and Information Services. Contact information
can be found on the NOAA CRSRA Web site at http://www.nesdis.noaa.gov/
CRSRA/. There is no application form, but the required information is listed in
Appendix 1 of 15 CFR Part 960. Submissions should be compiled in the same
order as listed in the appendix, and all fields in the application must be addressed
even if the answer is “none” or “N/A.”
For imagers designed to only take images of Earth, the application process is
fairly straightforward, and approval takes approximately 120 days following sub-
mission (separate from the initial contact form). NOAA will provide feedback
on draft applications prior to formal submission to help smooth out the process.
If the CubeSat is to image anything other than Earth (i.e. other CubeSats, LV
4 Spectrum Guidance for NASA Small Satellite Missions (https://www.nasa.gov/
directorates/heo/scan/spectrum/policy_and_guidance.html)
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 51

CubeSat
101
CHAPTER 5 Licensing Procedures
Students from the University of
Colorado Boulder sharing information
about the MinXSS mission with NASA
Administrator Charlie Bolden. MinXSS
is a science investigation to study solar
flares, active regions, the quiescent
Sun, and their impact on Earth’s upper
atmosphere built by students from
the University of Colorado at Boulder.
Launched by NASA’s CubeSat Launch
Initiative on the December 6, 2015
ELaNa IX mission on the fourth Orbital-
ATK Cygnus Commercial Resupply
Services (CRS) to the Space Station
and deployed on May 16, 2016.
[University of Colorado at Boulder]
upper stage during deployment, etc.), an NEI (Non-Earth Imaging) waiver will
need to be submitted as part of your application, which can add a significant
amount of time to the application process. Be sure to notify the mission integra-
tor as soon as possible of the details of your NOAA application. If the application
needs to be updated during the process, especially to add an NEI waiver, this will
restart the process from the beginning, so be sure to consider the mission opera-
tions prior to submitting your application.
WARNING!
If your licenses are not finalized before your CubeSat is integrated into its
dispenser, your CubeSat will not fly on that mission. It’s crucial to follow up on
all paperwork and make sure there are no delays in the process.
As a CubeSat operator, you will have some post-launch licensing responsibili-
ties. You must maintain the imaging license by submitting to regular audits and
on-site inspections of the CubeSat’s ground station and mission control center.
The auditor will check to make sure you’ve maintained the security precautions
that were specified in your license approval.
52 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CCuubbeeSSaatt
110011
Flight Certification Documentation
62
FFliNgAhtM C ePrrtoifciceastsion IN THIS CHAPTER
6.1 Orbital Debris Mitigation
Documentation
Compliance
6.2 Transmitter Surveys
6.3 Materials List
6.4 Mass Properties Report
6.5 Battery Report
6.6 Dimensional Verifications
This is where the rubber meets the road: now you must show the mission inte- 6.7 Electrical Report
6.8 Venting Analysis
grator, and CSLI, that your CubeSat is ready to fly. Each CubeSat developer
6.9 Testing Procedures/Reports
will need to supply specific documentation (i.e., deliverables or verification evi-
6.9.1 Day In The Life (DITL)
dence) showing that their CubeSat meets all of the requirements of the mission.
6.9.2 Dynamic Environment
The mission integrator will receive the deliverables and verify all requirements
Testing (Vibration/Shock)
have been met. When all items have been submitted and accepted, the approval 6.9.3 Thermal Vacuum Bakeout
for flight can be granted. Typically, the first of the deliverables will be due about Testing
10 months before the CubeSat is to be delivered to the integration site. 6.10 Compliance Letter
6.11 Safety Package Inputs (e.g.,
Missile System Prelaunch Safety
It is possible that your CubeSat design will change slightly during the mis-
Package, Flight Safety Panel)
sion cycle (i.e., the time between mission kickoff and CubeSat delivery), so it’s
important to keep the mission integrator aware of all changes and issues
encountered during the development of your CubeSat.
This chapter will outline the documents and describe the content typically Pictured above:
ASTERIA Spacecraft final
required for approval for flight. But remember, the mission integrator will supply
closeout at the Jet Propulsion
your team with the official list of deliverables for your mission, as well as specific
Laboratory. [JPL]
information that must be included in each document.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 53

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
Flight Certification Documentation List
1. Orbital Debris Assessment Report 7. Electrical report
(ODAR), or similar, showing
8. Venting analysis
compliance inputs
9. Testing procedures/reports
2. Transmitter surveys
10. Compliance letter
3. Materials list
11. Safety package inputs
4. Mass properties report
(e.g., Missile System Prelaunch
5. Battery report Safety Package—or MSPSP, flight
safety panel)
6. Dimensional verifications
6.1 Orbital Debris Mitigation Compliance
Orbital debris mitigation compliance is documented in an Orbital Debris
Assessment Report (ODAR), or similar document (however, for the purposes of
this guide, we’ll call everything an ODAR), and is the document that assures all
interested parties that your CubeSat won’t pose an unacceptable hazard to other
orbiting spacecraft, will deorbit in a reasonable amount of time, and that no
unacceptably large piece of your CubeSat is going to survive reentry when it deor-
bits and burns up in the atmosphere. The ODAR demonstrates compliance with
FCC, NOAA, or NASA requirements for safing and/or disposal of the spacecraft >>FREE ADVICE
and orbital debris mitigation requirements. The documentation required depends
CHOOSE LOW MELTING POINTS. It
on which U.S. Government agency has “jurisdiction” over your CubeSat as an
is strongly recommended that
on-orbit satellite. In general, if you will be required to get an FCC license, then
you avoid the use of materials
you will need to meet the FCC’s regulations on orbital debris mitigation and pro- with high-melting points in
vide a publicly-releasable document for their records. For CSLI CubeSats, this has your CubeSat design (e.g., use
traditionally been satisfied by providing the FCC the CubeSat-specific appendix aluminum and steel as opposed
to tantalum, titanium, or tungsten).
from the mission’s ODAR developed by NASA LSP (see next paragraph).
If any of your satellite’s materials
survive reentry, they pose a threat
For CSLI CubeSats, an ODAR document will be generated by NASA LSP using
to people and property. Use of
information provided by the CubeSat developer. The CubeSat developer will pro- such materials could lead to a
vide documents that include a mission description (including an expanded view constraint in licensing requiring
image of the spacecraft) and a list of all components on the satellite, identifying you to purchase insurance for
such an unfortunate occurrence.
the mass, shape, volume, and material of each. Be sure to note in the components’
descriptions any hazardous and exotic materials, propulsion, pressure vessels, and
power storage (include any UL numbers for batteries). Templates for each of these
two documents can be found in Appendix C.
54 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
For non-Government, non-CSLI CubeSats flying on a mission that requires the
CubeSat developer to provide their own ODAR, the developer should reference
the FCC requirements in the Code of Federal Regulations at 47 CFR 25.114(d)
(14)5 and, as appropriate, the NOAA requirements at 15 CFR 960 (Appendix 1
to Part 960, Section V,C.).6 The developer may use NASA’s Debris Assessment
Software (DAS) to complete the analysis and report. You can find the software
here: https://www.orbitaldebris.jsc.nasa.gov/mitigation/das.html. The DAS User’s
Guide gives step-by-step instructions on how to use DAS to complete the assess-
ment. Note that the FCC’s and NOAA’s requirements are, for the most part, a
The St. Thomas More Cathedral School
subset of the requirements imposed by NASA on NASA projects. students working on STMSat-1, an
education mission to provide hands-
on, inquiry-based learning activities
Drafts of your ODAR documentation will likely be among the first deliverables
with an on-orbit mission to photograph
due. Changes in design as development continues will mean you need to revise the Earth and transmit images to their
and resubmit the documents. Without an approved ODAR, NOAA and FCC primary ground station and to remote
ground stations throughout the country.
licenses will not be granted, and the CubeSat cannot be approved for flight.
STMSat-1 was the first CubeSat
NASA launched for a primary school.
Launched by NASA’s CubeSat Launch
6.2 Transmitter Surveys Initiative on the December 6, 2015
ELaNa IX mission on the fourth Orbital-
ATK Cygnus Commercial Resupply
The transmitter survey is a series of questions about the CubeSat’s communi-
Services (CRS) to the Space Station and
cation system. The information from the survey will be used to help the LV deployed on May 16, 2016. [St. Thomas
More Cathedral School]
provider perform EMI/EMC analysis and will be included in the MSPSP (see
Chapter 6.11) to verify that the CubeSat meets RF inhibit requirements. A tem-
plate for this document can be found in Appendix C.
A draft of this deliverable will likely be another of the first documents due. If you
make any changes in your design relevant to the transmitter after the transmitter
survey is submitted, you will need to revise and resubmit the document.
6.3 Materials List
The materials list will be used on CSLI missions to verify that no dangerous or
prohibited items have been incorporated into your CubeSat design. The materials
list is usually a Word document identifying every material used on the CubeSat
5 https://www.gpo.gov/fdsys/pkg/CFR-2016-title47-vol2/pdf/CFR-2016-title47-
vol2-part25-subpartB.pdf
6 https://www.gpo.gov/fdsys/pkg/CFR-2017-title15-vol3/pdf/CFR-2017-title15-
vol3-part960.pdf
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 55

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
along with its mass (or expected mass), its location on the CubeSat, and its out-
outgassing: In the spacecraft
gassing properties including Total Mass Loss (TML) and Collected Volatile
industry, outgassing refers to
Condensible Materials (CVCM). NASA has published outgassing properties for the sublimation or evaporation
most materials used in CubeSats; this information can be found at http://out- of materials as those materials
gassing.nasa.gov. Most ICDs use the outgassing limits identified in the CDS are taken to a high-vacuum
environment like space. The
requirements. A template for this document can be found in Appendix C.
material that is lost to outgassing
can find its way onto sensitive
Like the ODAR documents, a draft of this document will likely be among the
components and possibly affect a
first deliverables due. Any changes in your design during the development will
mission’s success.
require revision of the document and resubmission.
>>FREE ADVICE
6.4 Mass Properties Report
CHOOSE LOW-OUTGASSING. When
designing your CubeSat, use
The mass properties report identifies the CubeSat’s total mass, center of grav-
materials that are considered
ity (CG), moments of inertia (MOIs), and products of inertia (POI) relative to
“low-outgassing.” If you do
each axis. The first draft of this report will be among the first deliverables due. this, it’s possible that your
This gives the mission integrator and the LV provider adequate time to use the team can avoid performing a
thermal vacuum bakeout (see
mass property information in their analyses. The LV provider will use your initial
Chapter 6.9.3, Thermal Vacuum
mass estimates for their own LV load calculations. The mass properties that your
Bakeout Testing). The bakeout
CubeSat ends up with after being built must remain within your expected toler-
is a prelaunch measure used to
ances so that the LV provider’s calculations will remain valid.
force the CubeSat components’
materials to outgas in a safe
The first draft of the report will be reviewed to ensure the predicted mass and laboratory environment.
CG locations meet the ICD requirements. The final mass properties report will
include the CubeSat’s measured total mass and must be submitted as soon as
>>FREE ADVICE
possible after the final flight unit is complete.
CAREFULLY CONSIDER THE MASS
If your final mass properties numbers are out of tolerance, it’s possible the CubeSat ESTIMATE MARGINS. When you
will be demanifested. This is because a mass that is outside of the LV provider’s submit your data estimates for
the early LV provider’s analyses,
analysis creates an unknown risk to the LV and its primary mission.
be sure to include large, but
still reasonable, margins on all
In addition to providing mass properties information, the mass properties report
values. (Check with your mission
will typically be used to verify the CubeSat’s coordinate system with a drawing integrator for advice on margins
or schematic included in the report. for your estimated values.) When
the first mass properties draft is
due, most CubeSats are still in the
development stages, so it’s not
unusual for designs to change and
thus affect the mass properties.
56 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
6.5 Battery Report
The information provided in the battery report will be used to verify that proper
battery circuit protection is in place. Some mission integrators will require a
standalone report, while others may review a portion of the MSPSP in place of
the standalone report (the MSPSP will include all of this information). The mis-
sion integrator will sometimes require a battery lot testing report as well.
Specific information required for the battery report is listed below.
• Battery dimensions
• Battery UL number
• Manufacturer specification sheet
• Manufacturer part number
• Mass
• Battery model number
• Battery manufacturer
• Number of cells and their configuration (i.e., wired in series or parallel)
Daniel Perez, Ph.D., a graduate student
• Discharge characteristics
from the University of Miami, displays
a piece of the prototype structure for a
• Charge characteristics
new solid-state battery in the Prototype
• Lithium battery short circuit test Laboratory at NASA’s Kennedy Space
Center in Florida. The size of the battery
• Safety circuit diagram is so small that it could be a prime
candidate for use in microsatellites,
• If battery has been modified, provide all modification documentation
including CubeSats. [NASA]
• Technical datasheet that verifies battery circuit protection exists for bat-
tery charging/discharging
6.6 Dimensional Verifications
Your CubeSat will be expected to adhere to the dimensional requirements spec-
ified in the CubeSat-to-dispenser ICD. The mission integrator will require the
developer to perform a dimensional check after assembly, and prior to any envi-
ronmental testing, to ensure the CubeSat will fit into its flight dispenser. It’s
important to check your CubeSat’s dimensions often (before and after environ-
mental testing at a minimum).
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 57

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
A dimensional checklist example (CubeSat Acceptance Checklist, or CAC) can
be found in Appendix C. This is not an official template and may differ signifi-
cantly from what your mission integrator provides you, but it will give you an
idea of what will be expected.
6.7 Electrical Report
An electrical report will be used to verify a number of requirements listed in Remove Before Flight (RBF)
pin: The RBF pin is a physical
the CubeSat-to-dispenser ICD (e.g., number of RF inhibits, CubeSat being
object that separates the
self-contained).
CubeSat’s power system from the
rest of the circuitry (particularly
Specific information typically required for the electrical report is listed below.
the central processor). Ideally,
• Diagram of the electrical power systems the RBF pin is removed after the
CubeSat is integrated into the
• Highlights for the electrical inhibits within the electrical diagram flight dispenser, but it can be
• Identification of real-time clock circuitry within the diagram (if removed just prior to integration.
applicable)
• Identification of the Remove Before Flight (RBF) pin within the diagram separation switches: The
(if applicable) separation switches on the
CubeSat are usually located on
• Identification of the separation switch(es) within the diagram (if
the ends of the CubeSat rails.
applicable)
When depressed (as they will
• Clear explanation of the number of inhibits and how they function be in the dispenser) they will
physically separate the power
system circuitry from the rest
6.8 Venting Analysis
of the CubeSat circuitry. When
the CubeSat is ejected from the
As the launch vehicle ascends out of the atmosphere, it does so quickly, and the dispenser into orbit, the switches
surrounding air pressure decreases quickly. It is a concern that somewhere inside will no longer be depressed and
will allow the CubeSat circuitry to
your CubeSat is a trapped pocket of air that could possibly burst through the
connect to the power system.
structure during ascent. This could create a dangerous situation for the LV and
other payloads on the launch.
independent inhibit: An inhibit
The venting analysis deliverable is a relatively simple report that uses diagrams
is a physical device between
and some basic mathematics to show the mission integrator that your CubeSat has a power source and a hazard.
adequate venting to prevent the explosive decompression of any container in your A timer is not considered an
CubeSat as it makes the quick transition from standard atmosphere to vacuum. independent inhibit.
The venting analysis will clearly identify the ventable and non-ventable volumes,
and the venting area locations on the CubeSat. It will show that the internal
58 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
volume of air will safely evacuate through these venting locations. The CubeSat-
to-dispenser ICD will typically have a requirement for the acceptable venting
rate. If there are any volumes that cannot meet the requirement, additional anal-
ysis or testing may need to be performed by the CubeSat developer to show that
the structure is strong enough to handle the change in external air pressure.
The mission integrator will likely provide a report template to the CubeSat teams
on any CSLI mission.
6.9 Testing Procedures/Reports
A report will need to be submitted for each test used to verify CubeSat-to-
>>FREE ADVICE
dispenser ICD requirements. The reports will state which requirements are being
verified and the specific evidence in the report that verifies each requirement. A GET FEEDBACK ON TEST PROCEDURES
BEFORE TESTING. It’s advisable,
copy of the signed, as-run test procedures should be included in the report, along
and may be required, to send your
with pictures of the as-run test setup. These reports will likely be the last deliver-
testing procedures to the mission
ables submitted, since they can only be written after completion of the flight unit integrator for review before your
build. Generally, any data gathered from informal testing on an engineering unit team starts testing. If there’s
does not need to be included in this report. anything vital that’s missing in
the procedures, the mission
integrator will catch it and have
It’s important to report any anomalies encountered during and after testing,
you correct the issue before you
(including informal testing). So, what qualifies as an anomaly? An anomaly is
start. If you don’t have your test
anything that affects the ability of your hardware to meet the requirements, such plans reviewed before testing, it’s
as: damage to any part of the CubeSat, unexpected release of deployables, strange entirely possible that you will have
rattles, unexpected transmissions, evidence of unexpected power-on, or anything to retest your flight hardware.
else that could impact your schedule including anomalies with the test apparatus
itself. When in doubt, ask the mission integrator. If an anomaly occurs during
testing, you should stop the test, notify the mission integrator immediately, and
discuss paths forward before proceeding.
6.9.1 Day In The Life (DITL) Testing
This test shows that your CubeSat’s electronics and flight software work as
expected. The ICD will have requirements for when the CubeSat is allowed to
release its deployables and when it can start transmitting after being ejected from
the dispenser. It will also have requirements on the minimum number of inhibits
that will prevent early power-up of the CubeSat systems. This test will verify all
of those things.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 59

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
The DITL report will show that the CubeSat’s timers and inhibit design function DID YOU KNOW?
correctly, adhering to the appropriate mission ICD requirements. This test must
How DITL testing works
be run with the final flight software and in most cases will be required to be com-
In order to prove to the mission
pleted prior to environmental testing. This will allow the CubeSat to demonstrate
integrator that your CubeSat
when the deployables will be released without invalidating the vibration testing.
software will work as planned, you’ll
perform the DITL testing. The idea
After you’ve completed the DITL testing, you are not allowed to change any is to recreate what happens to your
piece of code in the software for any reason. Doing so will invalidate your test, CubeSat when it’s released from the
dispenser. To do this, you will start
and the mission integrator will require you to perform a retest and submit a new
by removing the RBF pin with the
test report.
separation switch(es) depressed,
just as if it were inside the dispenser.
The mission integrator will supply a report template, possibly with a generic set of
Then, to simulate the CubeSat
procedures, but the test will need to be tailored to your CubeSat’s specific inhibit being ejected, you will release the
structure. Your test procedure must be approved by the mission integrator prior separation switch(es) and time how
to testing. long it takes for the CubeSat to
start transmitting and release its
Minimum Report Content deployables. If this time is more than
• As-run procedures with all steps time stamped the minimum required in the ICD, the
CubeSat meets that requirement.
• Proof that separation switches function as required
• Proof that timers function as required
• Simulation of flight-like release of deployables
• Time of deployment
• Time of first transmission
Note: If you don’t want your CubeSat to release its deployables for this test, you
only need to show that they won’t be released within the minimum post–deploy-
ment time specified in the CubeSat-to-dispenser ICD.
6.9.2 Dynamic Environment Testing (Vibration/Shock)
HaloSat, developed by the University
The ride up to space on a typical LV can be pretty bumpy. Your CubeSat will of Iowa, is a science mission to map
the distribution of hot gas in the Milky
be subjected to a dynamic environment that shakes it really hard. The strength
Way and to determine whether it fills an
of these levels of vibration or shock can be higher or lower depending on the extended halo or the halo is compact
specific LV and the dispenser mounting configuration on the LV. The point of with little contribution to the total mass
of the galaxy. It will detect X-rays from
dynamic environment testing (also called environmental testing) is to show that
oxygen ions in the hot Galactic halo.
your CubeSat will survive the vibrations and shocks that it will experience during [Blue Canyon Technologies, Inc.]
launch. The CubeSat-to-dispenser ICD will specify the levels at which you’ll need
to shake your CubeSat for this test, as well as how long the test will need to last.
60 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
The DITL report will show that the CubeSat’s timers and inhibit design function DID YOU KNOW? There are two common types of dynamic testing: shock and vibration. Vibration
correctly, adhering to the appropriate mission ICD requirements. This test must testing (commonly referred to as vibe testing) is required for all launches, but
How DITL testing works
be run with the final flight software and in most cases will be required to be com- the launch vehicle provider does not always require shock testing. Testing can
In order to prove to the mission
pleted prior to environmental testing. This will allow the CubeSat to demonstrate be done in your own testing facilities, but if you don’t have the required capabil-
integrator that your CubeSat
when the deployables will be released without invalidating the vibration testing. ities, there are commercial testing facilities that you can work with for a price.
software will work as planned, you’ll
perform the DITL testing. The idea Costs can sometimes be managed if multiple CubeSats on the same manifest
After you’ve completed the DITL testing, you are not allowed to change any is to recreate what happens to your can share the test setup simultaneously—such as during shock testing. If your
piece of code in the software for any reason. Doing so will invalidate your test, CubeSat when it’s released from the organization has access to vibe or shock testing facilities (through a connection
dispenser. To do this, you will start
and the mission integrator will require you to perform a retest and submit a new to a local university, for example), that can be an inexpensive alternative to using
by removing the RBF pin with the
test report. a commercial facility.
separation switch(es) depressed,
just as if it were inside the dispenser.
The mission integrator will supply a report template, possibly with a generic set of Then, to simulate the CubeSat Your environmental testing reports need to show that your CubeSat flight unit
procedures, but the test will need to be tailored to your CubeSat’s specific inhibit being ejected, you will release the was tested to the levels prescribed in the CubeSat-to-dispenser ICD. It also needs
structure. Your test procedure must be approved by the mission integrator prior separation switch(es) and time how to show that the CubeSat was structurally intact after testing (verified by visual
to testing. long it takes for the CubeSat to inspection, and from responses of pre- and post- test sine sweeps), and that the
start transmitting and release its
CubeSat did not transmit or power-on in accordance with the ICD requirements.
Minimum Report Content deployables. If this time is more than
Salish Kootenai College student
• As-run procedures with all steps time stamped the minimum required in the ICD, the
Zachary DuMontier tests solar
CubeSat meets that requirement. The mission integrator will supply a template for the test procedure and report.
panels on BisonSat. The BisonSat
• Proof that separation switches function as required The report must include the control/input data, response of the test article (if
mission is an Earth Science mission
• Proof that timers function as required applicable), and pictures of the test setup, with special attention given to the that will demonstrate the acquisition
of 100-meter or better resolution
accelerometer locations. Before testing can begin, the mission integrator needs to
• Simulation of flight-like release of deployables visible light imagery of Earth using
review your testing procedures to make sure the test will verify all of the appro- passive magnetic stabilization from a
• Time of deployment priate ICD requirements. CubeSat. BisonSat is the first CubeSat
designed, built, tested, and operated
• Time of first transmission
by tribal college students. Launched by
After you’ve completed the environmental testing, you are not allowed to
NASA’s CubeSat Launch Initiative on
make any physical changes to the hardware (i.e., no removing panels, no the ELaNa XII mission as an auxiliary
Note: If you don’t want your CubeSat to release its deployables for this test, you
payload aboard the NROL-55 Mission
unscrewing fasteners, no releasing deployables, etc.) for any reason. Doing
only need to show that they won’t be released within the minimum post–deploy- on October 8, 2015. [Salish Kootenai
ment time specified in the CubeSat-to-dispenser ICD. so will invalidate your test, and the mission integrator will require you to perform College]
a retest and submit another test report.
Minimum Report Content
6.9.2 Dynamic Environment Testing (Vibration/Shock)
• As-run procedures with all steps time-stamped
The ride up to space on a typical LV can be pretty bumpy. Your CubeSat will • Photos of the test setup, including accelerometer locations
be subjected to a dynamic environment that shakes it really hard. The strength
• Plots of the test data showing the test durations and levels
of these levels of vibration or shock can be higher or lower depending on the
• Proof that the CubeSat survived testing
specific LV and the dispenser mounting configuration on the LV. The point of
dynamic environment testing (also called environmental testing) is to show that
your CubeSat will survive the vibrations and shocks that it will experience during
launch. The CubeSat-to-dispenser ICD will specify the levels at which you’ll need
to shake your CubeSat for this test, as well as how long the test will need to last.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 61

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
6.9.3 Thermal Vacuum Bakeout Testing
Bakeout
During the thermal vacuum (TVAC) bakeout test, the CubeSat is heated to
prescribed temperatures while in a high-vacuum environment. This bakeout is
required on almost all missions, primarily to allow the CubeSat’s materials to
outgas any possible contaminants before the actual launch. The primary pay-
load is sometimes very sensitive to contaminants, and many materials will release
small amounts of matter as the air pressure decreases to vacuum. Performing the
bakeout ensures that any matter that would have been released during launch is
safely released during the bakeout instead.
The ICD will state the required temperatures and target vacuum level that your
CubeSat will need to be tested to, as well as how long the CubeSat needs to be at
each temperature and vacuum level.
The test report needs to show that the CubeSat was subjected to thermal and
vacuum levels in accordance with the CubeSat-to-dispenser ICD requirements.
The mission integrator will supply a template for the test procedure and report.
Your report must include the control/input data, response of the test article (if
applicable), and pictures of the test setup, with special attention to thermocouple,
or temperature sensor, locations. Before testing begins, the mission integrator
needs to review your testing procedures to make sure the test will verify all of the
appropriate ICD requirements.
Minimum Report Content
• Time-stamped logs to show proper temperature and vacuum levels were
maintained
• Photos of the test setup, including thermocouple locations
• Plots of the test data showing the temperature levels and durations
• Plots of the test data showing the vacuum levels and durations
• Proof that the CubeSat survived testing
Cycling
Another type of TVAC testing is TVAC cycling. CubeSat developers aren’t usu-
ally required to perform this type of testing on their CubeSat, but it can help
screen for problems caused by the thermal cycling on orbit and help improve the
odds of your mission’s success. The reason you’ll want to put your CubeSat (or
even just the components) through TVAC cycling is to be confident that your
62 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
A student from Thomas Jefferson
High School of Alexandria, Virginia
conducting vibration testing on the
TJ3Sat CubeSat. It was developed to
create educational resources through
which other K-12 institutions can learn
about aerospace engineering and be
encouraged to seek careers in the
STEM fields. The primary payload is
a voice synthesizer module that takes
written phrases in the form of code and
produces a phonetic voice reading on
the satellite’s downlink frequencies.
Launched by NASA’s CubeSat Launch
Initiative on the ELaNa IV mission as
an auxiliary payload aboard the U.S.
Air Force-led Operationally Responsive
Space (ORS-3) Mission on November
19, 2013. [Thomas Jefferson High
School]
CubeSat can handle the vacuum and temperature range without being damaged.
You’ll want to know before you send your CubeSat to space that your solder joints
won’t break, and that the battery package isn’t going to melt away. For testing lev-
els and cycle repetitions, check out the CubeSat Requirements Document, LSP-
REQ-317.01, which is available on the NASA Web site at https://www.nasa.gov/
pdf/627972main_LSP-REQ-317_01A.pdf. It lays out a good guideline for this test.
TVAC cycling is typically just an internal test that you perform for yourself,
so you probably won’t be required to submit a report to the mission integrator.
However, in the interest of good record keeping, you should still write up a report
and procedures that your team can refer back to in the future.
WARNING!
Cycle testing is completely different from bakeout testing and cannot be
performed in place of your bakeout.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 63

CubeSat
101
CCHHAAPPTTEERR 66 FFlliigghhtt CCeerrttiifificcaattiioonn DDooccuummeennttaattiioonn
6.10 Compliance Letter
The compliance letter is signed by the CubeSat principal investigator. The letter
principal investigator: The
is essentially a statement from the CubeSat developer guaranteeing that your
principal investigator (PI) is the
CubeSat is compliant with the entire CubeSat-to-dispenser ICD, and that no
official leader of the CubeSat
prohibited components are aboard. project and is specified in the
project’s proposal. For university
The mission integrator will typically send a draft letter to the CubeSat teams for CubeSats, this position is filled by
the faculty member who is most
signature.
responsible for the project.
This deliverable is typically one of the last items due. A generic example is
included in Appendix C.
6.11 Safety Package Inputs (e.g., Missile System
Prelaunch Safety Package, Flight Safety Panel)
Depending on the type of mission model the CubeSat is participating in, you
will probably be required to submit documents with information specifically for
range safety, such as the Missile System Prelaunch Safety Package (MSPSP) or
the Flight Safety Panel (for Space Station missions).
The CubeSat developer typically is responsible for creating the MSPSP, but the
mission integrator will create a template, with instructions, for the CubeSat
teams to complete. In some cases, the mission integrator will write the MSPSP
for the CubeSats, but that will still require detailed information from the
CubeSat developer.
The document covers all the hazards that the CubeSat could pose to the LV,
the dispenser, other CubeSats, and personnel handling or in proximity of the
CubeSat. You will be required to complete the MSPSP early to support any LV
provider analyses and ensure that your CubeSat design is safe to fly.
The mission integrator typically will supply a template to help the CubeSat devel-
oper create an MSPSP. The CubeSat MSPSP will outline any potential hazards
and how each is mitigated. Your final MSPSP documentation generally needs to
be submitted at least 45 days prior to arrival at the range, or launch facility. Your
mission integrator will set a deadline well ahead of the official due date and will
submit the MSPSP through the appropriate channels.
64 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
Pictured above:
A set of NanoRacks CubeSats is photographed
by an Expedition 38 crew member after the
deployment by the NanoRacks Launcher attached
A  List of Abbreviations
to the end of the Japanese robotic arm. [NASA]
ADCS  attitude determination and control system ICD  Interface Control Document
AFSPCMAN  Air Force Space Command Manual IRC  Internet Relay Chat
AFOSHSTD  Air Force Occupational Safety And Health  ISS  International Space Station
|       | Standard                                | ITU    | International Telecommunication Union |
| ----- | --------------------------------------- | ------ | ------------------------------------- |
| AoPO  | Announcement of Partnership Opportunity |        |                                       |
|       |                                         | JSpOC  | Joint Space Operations Center         |
Auxiliary Payload Integration Contractor
| APIC  |                              | LSP  | Launch Services Program |
| ----- | ---------------------------- | ---- | ----------------------- |
| CAC   | CubeSat Acceptance Checklist |      | launch vehicle          |
LV
California Polytechnic State University
| Cal Poly  |     | MOI  | moment of inertia |
| --------- | --- | ---- | ----------------- |
CDS  CubeSat Design Specification MRR  Mission Readiness Review
| CFR  | Code of Federal Regulations |        |                                         |
| ---- | --------------------------- | ------ | --------------------------------------- |
|      |                             | MSPSP  | Missile System Prelaunch Safety Package |
CG  center of gravity NASA  National Aeronautics and Space Administration
| CIR  | CubeSat Interface Review |      |                   |
| ---- | ------------------------ | ---- | ----------------- |
|      |                          | NEI  | Non-Earth Imaging |
Concept of Operations
CONOPS  NOAA  National Oceanic and Atmospheric Administration
| CRADA  | Cooperative Research And Development  |      |                                |
| ------ | ------------------------------------- | ---- | ------------------------------ |
|        |                                       | NRO  | National Reconnaissance Office |
Agreement
|     |     | NTIA  | National Telecommunications and Information  |
| --- | --- | ----- | -------------------------------------------- |
Commercial Remote Sensing Regulatory Affairs
| CRSRA  |     |     | Administration |
| ------ | --- | --- | -------------- |
CSLI  CubeSat Launch Initiative ODAR  Orbital Debris Assessment Report
| CVCM  | collected volatile condensible materials  |      |                                |
| ----- | ----------------------------------------- | ---- | ------------------------------ |
|       |                                           | ORS  | Operationally Responsive Space |
| DAS   | Debris Assessment Software                | OSL  | Office of Space Launch         |
| DITL  | Day in The Life                           |      |                                |
|       |                                           | PCB  | printed circuit board          |
DOD  Department of Defense P-POD Poly-Picosatellite Orbital Deployer
| ELaNa  | Educational Launch of Nanosatellites  |     |                      |
| ------ | ------------------------------------- | --- | -------------------- |
|        |                                       | RBF | Remove Before Flight |
Expendable Launch Vehicle
| ELV  |     | RF  | radio frequency |
| ---- | --- | --- | --------------- |
EMI/EMC  electromagnetic interference/electromagnetic  RFP Request for Proposal
compatibility
|     |     | SSDL | Space Systems Development Laboratory |
| --- | --- | ---- | ------------------------------------ |
ETU
|       | engineering test unit              | TLE  | Two Line Element         |
| ----- | ---------------------------------- | ---- | ------------------------ |
| EWR   | Eastern and Western Range          |      |                          |
|       |                                    | TML  | total mass loss          |
| FCC   | Federal Communications Commission  |      |                          |
|       |                                    | TNC  | terminal node controller |
| GSE   | Ground Support Equipment           |      |                          |
|       |                                    | TVAC | thermal vacuum           |
| IARU  | International Amateur Radio Union  |      |                          |
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative 65

CubeSat
101
Appendices
B Glossary
Attitude The Attitude Determination and Control System (ADCS) is the system designed to stabilize
Determination and and orient the CubeSat toward a given direction. This is a critical system for mission
Control Systems success. If the satellite needs to point its solar panels toward the Sun to get the most power
possible or if you are taking images of the Earth its attitude has to be set to the correct
value.
breadboard A breadboard is a board used to make an experimental model of components for testing.
CubeSat Design The CubeSat Design Specification (CDS) is a set of general requirements for all CubeSats,
Specification but is not the official set of requirements that you will need to follow for your launch.
CubeSat developer You’ll hear this term a lot in the CubeSat world. This is the standard term for any person or
organization that is designing, building, and preparing a CubeSat for flight.
deliverables A deliverable is anything that your team has agreed to submit to the mission integrator as
part of your legal obligations under the CRADA. These deliverables will be used to verify
that your CubeSat meets the requirements set in the mission ICD. Chapter 6 describes the
deliverables required on a typical CubeSat mission.
electrical inhibit An electrical inhibit is a physical device that interrupts the “power path” needed to turn on
your CubeSat and/or other potentially hazardous devices.
Engineering Test An engineering test unit (ETU) is built like the flight unit, but is not intended for launch.
Unit Developers will typically use the ETU like a practice dummy. It can be used to practice
putting the components together, fit checks, hardware and software testing, and anything
else that you don’t want to try for the first time on your valuable flight unit.
FlatSat A FlatSat is exactly what it sounds like. It’s an engineering unit of the CubeSat that includes
all of the components, except the structure. Typically, the components are mounted on
some sort of flat board, hence the term FlatSat. Developers can use the FlatSat to test and
troubleshoot the CubeSat’s systems without integrating everything onto the structure.
form factor This is a term used to describe the size, shape, and/or component arrangement of a
particular device. When we use it in reference to the standard CubeSat, we’re referring to
the specific size and mass that defines a CubeSat.
independent inhibit An inhibit is a physical device between a power source and a hazard. A timer is not
considered an independent inhibit.
integration services This normally includes, at a minimum, review of your deliverables, the dispenser, integrating
your CubeSat into the dispenser, any testing that is done on the dispenser/CubeSat system,
and physically integrating the dispenser/CubeSat system onto the launch vehicle.
66 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
interface “Interface” is a general term that refers to any point where two or more components are
joined together. For instance, someone may ask, “How does the CubeSat interface with the
dispenser?” or, “Is there an electrical interface between the CubeSat and the Dispenser?”
(These questions mean, “Can I electrically connect the CubeSat to the dispenser
somehow?”)
investigation This term gets used often when talking about a CubeSat’s mission. It refers to the
investigation, scientific or otherwise, that your CubeSat will be performing. In this context,
“investigation” is commonly used interchangeably with a CubeSat “mission.”
manifesting The process of assigning CubeSats to the available slots on a launch opportunity.
margin This is a very common term in the engineering world specifically referring to the safety
margin, but is more generally used to refer to extra anything that gives you peace of mind.
When you’re talking about scheduling, you add time, or margin, in case you run into issues
or just estimate incorrectly.
mission This term is a somewhat generic, all-encompassing term that refers to the enterprise as a
whole. It’s sometimes used interchangeably with “project” or “investigation” and includes
all phases from development, testing, integration, to launch and operations.
mission integrator You may be asking yourself why the mission integrator isn’t called the mission coordinator.
Well, sometimes they are. The terms “integration” and “coordination” when referring
to a mission are commonly used interchangeably. For the purposes of this document,
the person/organization responsible for the coordination will be referred to as “mission
integrator,” and we’ll use “mission coordination” to refer to mission coordination activities.
outgassing In the spacecraft industry, outgassing refers to the sublimation or evaporation of materials
as those materials are taken to a high-vacuum environment like space. The material that
is lost to outgassing can find its way onto sensitive components and possibly affect a
mission’s success.
payload In the aerospace industry, “payload” is a general term used to describe the cargo (e.g.,
a satellite or spacecraft) being delivered to space. When we’re talking about CubeSat
dispensers, the payload always refers to the CubeSat.
principal investigator The principal investigator (PI) is the official leader of the CubeSat project and is specified in
the project’s proposal. For university CubeSats, this position is filled by the faculty member
who is most responsible for the project.
range safety Range safety is the person designed to protect people and assets on both the rocket
launch range and downrange in cases when a launch vehicle might expose them to danger.
Remove Before The Remove Before Flight (RBF) pin is a physical object that separates the CubeSat’s
Flight pin power system from the rest of the circuitry (particularly the central processor). Ideally, the
RBF pin is removed after the CubeSat is integrated into the flight dispenser, but it can be
removed just prior to integration.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 67

CubeSat
101
Appendices
separation switches The separation switches on the CubeSat are usually located on the ends of the CubeSat
rails. When depressed (as they will be in the dispenser) they will physically separate the
power system circuitry from the rest of the CubeSat circuitry. When the CubeSat is ejected
from the dispenser into orbit, the switches will no longer be depressed and will allow the
CubeSat circuitry to connect to the power system.
SpaceCap Notice The Space notification system PC Capture, or SpaceCap, is a software file containing
information about transmitting stations in space, including details about antennas,
transmitters, and the station itself. The file is created by PC-based software that can be
downloaded for free from the International Telecommunications Union (ITU) Web site.
http://www.itu.int.
strategic partnering Sometimes a CubeSat mission is too ambitious for a single organization to undertake. In
that case, a strategic partnership can combine the strengths and resources of multiple
organizations to achieve greater goals. These strategic partnerships are typically formalized
by some kind of formal agreement.
Terminal Node The Terminal Node Controller (TNC) is a device used by amateur radio operators to
Controller participate in AX.25 packet radio networks. It will assemble the data into packets of
information and key the transmitter to send the packets of data to the ground station. Once
the ground station receives the packets, the packets are reassembled and encoded to a
form that can be interpreted by your ground station.
Two Line Elements A Two Line Element (TLE) is a data format encoding a list of orbital elements of an Earth-
orbiting CubeSat for a given point in time, the epoch. Using a prediction formula, a TLE
can be used to estimate the position and velocity in the past, present or future for your
CubeSat.
68 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
C Templates
1 ODAR Inputs
NASA Orbital Debris Assessment Report Inputs
ELaNa # ODAR
Satellite Name – Organization – Satellite Size
Insert expanded-view image here with labels for major components, pay
particular attention to re-entry concern materials, if any (metals with high
melting point, ceramics, glass, etc.). This can be the same image used in
the CubeSat Interface Review (CIR).
Brief Overview: Describe the satellite and mission objectives.
CONOPS: Give a rough description of activities from P-POD deployment
to end of life. Mention any activities or deployments that may be of interest
from an orbital debris standpoint.
Materials: Describe the major materials used in the satellite with particular
attention to anything potentially capable of surviving reentry. Items listed
here should agree with the ODAR spreadsheet.
Hazards: State whether there are any hazardous systems on the satellite.
Batteries: Describe the power system and make note of the UL listing num-
ber for the batteries. This is to provide confidence that the batteries have
the proper safety mechanisms in place and will likely not create additional
orbital debris.
Example submission is on the following page.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 69

CubeSat
101
Appendices
ELaNa II ODAR
CubeSat-1 – Example University – 1U
CubeSat-1 will demonstrate the use of commercial off-the-shelf (COTS)
components in space, test a high-speed communications link, and character-
ize an Earth observation imager.
Upon deployment from the P-POD, CubeSat-1 will power up and start
counting down timers. At 30 minutes, the antennas will be deployed, then
at 45 minutes the UHF beacon will be activated. For the first few passes, the
ground station operators will attempt communications to perform checkouts
of the spacecraft. Approximately 4 days from launch, payload tests will begin
and continue for at least 1 year.
The CubeSat structure is made of Aluminum 6061-T6. It contains all stan-
dard commercial off-the-shelf (COTS) materials, electrical components,
PCBs, and solar cells. The high-speed radio uses a ceramic patch antenna.
There are no pressure vessels, hazardous, or exotic materials.
The electrical power storage system consists of common lithium-ion batteries
with over-charge/current protection circuitry. The lithium batteries carry the
UL-listing number MH12345.
70 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
2   CubeSat Components ODAR Template
NASA CubeSat Components ODAR Template
External/Internal
| Row  | (Major/Minor  |     | Body  Mass  | Diameter/  | Length  Height  |
| ---- | ------------- | --- | ----------- | ---------- | --------------- |
No. Name Components) Qty Material Type (g) Width (mm) (mm) (mm)
| 1 CubeSat Name |     | 1 e.g., Aluminum  | Box |     |     |
| -------------- | --- | ----------------- | --- | --- | --- |
6061
| 2 CubeSat      | External – Major | 1 e.g., Aluminum    | Box |     |     |
| -------------- | ---------------- | ------------------- | --- | --- | --- |
| Structure      |                  | 6061                |     |     |     |
| 3 Antennae     | External – Major | xxx e.g., Steel 410 |     |     |     |
| 4 Solar Panels | External – Major | e.g., Fiberglass    |     |     |     |
| 5 Sep Switches | External – Minor |                     |     |     |     |
| 6 Any other    | External – Minor |                     |     |     |     |
external
components
| 7 Batteries | Internal – Major |     |     |     |     |
| ----------- | ---------------- | --- | --- | --- | --- |
8 ADCS
Components
(e.g., Magnets)
9 Payload Board
10 Comm Board
11 Battery Board
12 C&DH Board
| 13 Fasteners      | Internal – Minor |              |     |     |     |
| ----------------- | ---------------- | ------------ | --- | --- | --- |
| 14 Cabling, etc.  | Internal – Minor | e.g.,Copper  |     |     |     |
alloy
Guide/Descriptions of Each Column
| Row Number:  List components in decreasing importance (follow column C) |     |     |     |     |     |
| ----------------------------------------------------------------------- | --- | --- | --- | --- | --- |
Name:  List your CubeSat first as the parent and each component and subsystem associated with your CubeSat
External/Internal:  Rank CubeSat components from external to internal and major to minor
| Qty:  List the quantity of component |     |     |     |     |     |
| ------------------------------------ | --- | --- | --- | --- | --- |
Material:  List the parent material for the component, specify alloy type if possible
| Body Type:  List the general shape of the component      |     |     |     |     |     |
| -------------------------------------------------------- | --- | --- | --- | --- | --- |
| Mass:  List the mass of the component in grams           |     |     |     |     |     |
| Dimensions:  List the width/length/height in millimeters |     |     |     |     |     |
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative 71

CubeSat
101
Appendices
3 Transmitter Survey
All CubeSats shall provide transmitter data addressing the topics below, including
their primary and secondary communications system (e.g., 70 cm and S-Band).
This data shall satisfy the requirements set forth in the CubeSat-to-dispenser ICD.
1. Transmitter Type: Enter the generic class of the transmitter. The gen-
eral modulation type and transmitter purpose should be entered
as a two- or three-word description. Examples are as follows: FM
Communications, Pulse Doppler Radar, 802.11b Wireless LAN, FSK
Data Communications, Spread-Spectrum Communications, etc.
2. Tuning Range: Enter the frequency range (e.g., 225–400) and units
(e.g., kHz, MHz or GHz) over which the transmitter is capable of being
tuned. For equipment designed to operate only at a single frequency,
enter this frequency. The entry should be the lowest tunable center fre-
quency through the highest tunable center frequency. If the equipment
is designed for use at a single frequency only, cannot be tuned, or in any
way adjusted in frequency, the center frequency of the emission or recep-
tion should be listed in this block.
3. Filter Employed: If a filter is employed between the final radio frequency
(RF) stage and the transmitter antenna, it should be indicated here and
information on the type of filter (e.g., lowpass, highpass, or bandpass) as
well as any additional specifications should be provided here. An exam-
ple of this additional information would be an entry such as this one:
“Low-Pass filter with 1.5-dB insertion loss and a minimum of 85-dB
attenuation 25 MHz removed from the tuned frequency.”
4. Emission Bandwidth: This item should contain information regarding
the spectral energy distribution of the transmitted signal. The emission
bandwidth is defined as the signal appearing at the antenna terminals
and includes any significant attenuation contributed by filtering in the
output circuit or transmission lines. The bandwidths of the signals at
points –3, –20, and –60 dB, relative to the fundamental signal level,
are required, and should not include tuning range or carrier movement.
The bandwidth at –40 dB shall also be entered if the transmitter is a
pulsed radar transmitter. Values of emission bandwidth specified should
be indicated as calculated or measured. Indicate units used (e.g., Hz,
kHz, or MHz).
72 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
5. Power (As-Deployed): Enter the mean power delivered to the antenna ter-
minals for all AM- and FM-type emissions as the satellite will be deployed
on orbit. For all other classes of emissions, enter the peak envelope power
(PEP). Any unique situations such as interrupted continuous wave (CW),
should be provided in detail. Indicate the units (e.g., W or kW).
6. Power (Maximum Hardware Capability): Enter the mean power delivered
to the antenna terminals for all AM- and FM-type emissions assuming
maximum capability of the transmitter. For all other classes of emis-
sions, enter the peak envelope power (PEP). Any unique situations, such
as interrupted continuous wave (CW), should be provided in detail.
Indicate the units (e.g., W or kW).
7. Harmonic Level: All RF transmitters emit energy at various places in the
spectrum outside the necessary bandwidth. These out-of-band emissions
are referred to as “spurious emissions.” The highest levels of spurious
energy generally occur at frequencies that are multiples or “harmonics”
of the center frequency. Thus, a transmitter tuned to 30 MHz will also
emit energy on 60 MHz, 90 MHz, 120 MHz, etc. This section requires
the second, third, and “other” harmonic power level specified in decibels
relative to the peak output power of the carrier signal (dBc). The second
harmonic emission falls at the frequency equal to two times the funda-
mental frequency. Similarly, the third harmonic falls at the frequency
equal to three times the fundamental frequency. Harmonic emission
power levels tend to decrease as the harmonic frequencies increase. Thus,
the second harmonic power level is generally greater than the third, with
the third expected to be greater than the fourth. The carrier signal, or
fundamental emission, is always designated as 0 dB. Thus, a harmonic
or spurious emission with a peak power of 80 dB below that of the fun-
damental has a relative level of –80 dBc. The level should always be
expressed as a relative dB level, never as an absolute level (dBm or dBW).
Whenever possible, the power levels should be measured from the radi-
ated spectrum of the transmitter. If radiated spectrum measurements
are not possible, the power levels should be measured at the antenna
terminals. Indicate where the measurement was made (radiated, antenna
terminals, or transmitter final stage).
8. Spurious Level: Enter the maximum value of spurious emission in dB
relative to the fundamental, which occurs outside the –60-dBc point on
the transmitter fundamental emission spectrum but does not occur on a
harmonic of the fundamental frequency.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 73

CubeSat
101
Appendices
4 Materials List
Launch Service Program – Standard Materials List Form
CubeSat Developer: ____________________________________________________________________
CubeSat Name: _______________________________________________________________________
Date Provided: _______________________________________________________________________
Purpose: The purpose of this document is to provide a listing of materials that have been selected for use in the
CubeSats.
TABLE 1. Metals
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
TABLE 2 – Non-Metal
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
74 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
TABLE 3 – Surface Coatings
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
TABLE 4 – Elastomerics
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
TABLE 5 – Adhesives
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 75

CubeSat
101
Appendices
TABLE 6 – Miscellaneous
Data
Item # Material ID Specification Description % TML % CVCM Location Reference
Notes:
N/A Non-Applicable
N/D No Data Available
76 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
5 Compliance Letter
[Optional Header Logo]
[Insert Date]
[Mission Integrator POC Name]
[Mission Integrator Organization]
[Mission Integrator Address]
[Mission Integrator Address]
Dear __________,
This memo is to certify that [Insert CubeSat Name] and [Insert CubeSat Team
Name] is in compliance with all requirements in the CubeSat to Dispenser
Interface Control Document for the [Insert Mission Name] Mission [Insert ICD
doc ID#].
This compliance includes the following: [ICD verification statements below are
examples, insert statements specific to current mission ICD]
• 3.1.1 CubeSat Design
• The CubeSats shall be self-contained and provide their own
power, sequencing, and wiring.
• 3.1.2 Pressure Vessels
• The CubeSat shall not contain pressurized vessels.
• 3.1.3 Propulsion Systems
• The CubeSat shall not contain propulsion systems.
• 3.1.4 Radioactive Material
• The CubeSat shall not contain radioactive material that,
unshielded, would produce personnel exposure greater than the
Nuclear Regulatory Commission limit for members of the gen-
eral public in any unrestricted area.
• 3.1.5 Explosive Devices
• The CubeSat shall not contain explosive devices.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 77

CubeSat
101
Appendices
• 3.3.5.1 CubeSat Transmissions through Ground Command
• The CubeSat operations plan shall prevent ground-commanded
activation of any CubeSat transmissions prior to 45 minutes
after on-orbit deployment from the P-POD.
For requirement 3.3.5.1 I certify that [CubeSat Team Name] ground operations
procedures will restrict issuance of ground commands until 45 minutes after the
confirmed separation time of the CubeSat from the P-POD.
Sincerely,
[Principal Investigator Signature Block]
[PI Name Typed]
[PI Title]
[Institution]
78 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
6   CubeSat Acceptance Checklists
1U CubeSat Acceptance Checklist
| Project:         |     |     | Date/Time:      |     |     | Engineers: |                           |     |     |
| ---------------- | --- | --- | --------------- | --- | --- | ---------- | ------------------------- | --- | --- |
| Organization:    |     |     | Location:       |     |     |            |                           |     |     |
| Satellite Name:  |     |     | Satellite S/N:  |     |     |            | Revision Date: 02/20/2014 |     |     |
Mass (< 1.33 kg) _________________ RBF Pin (≤ 6.5 mm) _________________
| Spring Plungers  |     | Functional Y / N          |     |     | Rails Anodized |     |     | Y / N |     |
| ---------------- | --- | ------------------------- | --- | --- | -------------- | --- | --- | ----- | --- |
| (Depressed)      |     | Flush with Standoff Y / N |     |     |                |     |     |       |     |
Deployment Switches  Functional Y / N  Deployables Constrained Y / N
| (Depressed) |     | Flush with Standoff Y / N |     |     |     |     |     |     |     |
| ----------- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
Mark on the diagram the locations of the RBF pin, connectors, deployables, and any envelope violations.
Rail 1
(+X,–Y)
Authorized by:
Rail 4
(+X,+Y)
IT 1: _________
Side 5
(–Z)
|     |     |     |     | Access |        |      |     |     | IT 2: _________ |
| --- | --- | --- | --- | ------ | ------ | ---- | --- | --- | --------------- |
|     |     |     |     | Port   | Side 1 |      |     |     |                 |
|     |     |     |     |        |        | (–Y) |     |     | Passed: Y / N   |
Access
Port Side 3
(+Y)
Rail 2
|     |     |     |     |     | Side 6 |     | (–X,–Y) |     |     |
| --- | --- | --- | --- | --- | ------ | --- | ------- | --- | --- |
(+Z)
Side 2
Side 4
| (–X) |     |     | (+X) |     |     |     |     |     |     |
| ---- | --- | --- | ---- | --- | --- | --- | --- | --- | --- |
Rail 3
(–X,+Y)
| List Item   |     |             |             | As Measured |             |     |             |     | Required |
| ----------- | --- | ----------- | ----------- | ----------- | ----------- | --- | ----------- | --- | -------- |
| Width [x–y] |     | Side 1 (–Y) | Side 2 (–X) |             | Side 3 (+Y) |     | Side 4 (+X) |     |          |
+Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Middle ____________ ____________ ____________ ____________ 100 ± 0.1 mm
–Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Height [x–y] Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
____________ ____________ ____________ ____________ 113.5 ± 0.1 mm
|     | Rail 1 (+X, –Y)  |                | Rail 2 (–X, –Y)  |     | Rail 3 (–X, +Y)  |     | Rail 4 (+X, +Y)  |     |     |
| --- | ---------------- | -------------- | ---------------- | --- | ---------------- | --- | ---------------- | --- | --- |
|     |                  | length x width | length x width   |     | length x width   |     | length x width   |     |     |
+Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
–Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
Protrusions Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X) Side 5 (–Z) Side 6 (+Z)
|     | _________ | _________ |     | _________ | _________ | _________ |     | _________ | ≤ 6.5 mm |
| --- | --------- | --------- | --- | --------- | --------- | --------- | --- | --------- | -------- |
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative 79

CubeSat
101
Appendices
1.5U CubeSat Acceptance Checklist
| Project:         |     |     |     | Date/Time:      |     |     | Engineers: |                           |     |     |
| ---------------- | --- | --- | --- | --------------- | --- | --- | ---------- | ------------------------- | --- | --- |
| Organization:    |     |     |     | Location:       |     |     |            |                           |     |     |
| Satellite Name:  |     |     |     | Satellite S/N:  |     |     |            | Revision Date: 02/20/2014 |     |     |
Mass (< 2.00 kg) _________________ RBF Pin (≤ 6.5 mm) _________________
| Spring Plungers  |     |     | Functional Y / N          |     |     | Rails Anodized |     |     | Y / N |     |
| ---------------- | --- | --- | ------------------------- | --- | --- | -------------- | --- | --- | ----- | --- |
| (Depressed)      |     |     | Flush with Standoff Y / N |     |     |                |     |     |       |     |
Deployment Switches  Functional Y / N  Deployables Constrained Y / N
| (Depressed) |     |     | Flush with Standoff Y / N |     |     |     |     |     |     |     |
| ----------- | --- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
Mark on the diagram the locations of the RBF pin, connectors, deployables, and any envelope violations.
Side 2
(–X)
Authorized by:
| Access |     |     | Access |     |     |     |     |     |     | IT 1: _________ |
| ------ | --- | --- | ------ | --- | --- | --- | --- | --- | --- | --------------- |
Port
Port
IT 2: _________
|     |     |     |     |     | Side 6 |     |        |     |     | Passed: Y / N |
| --- | --- | --- | --- | --- | ------ | --- | ------ | --- | --- | ------------- |
|     |     |     |     |     | (+Z)   |     | Rail 3 |     |     |               |
Rail 2
(–X,+Y)
(–X,–Y)
Side 1
(–Y)
Side 3
|     |     |     |     |     |     | Rail 4 (+Y) |     |     |     |     |
| --- | --- | --- | --- | --- | --- | ----------- | --- | --- | --- | --- |
Rail 1
(+X,+Y)
|     |     |     | (+X,–Y) |     |     |     |     | Side 5 |     |     |
| --- | --- | --- | ------- | --- | --- | --- | --- | ------ | --- | --- |
(–Z)
Access
|     |     |     |     |     | Side 4 | Port |     |     |        |     |
| --- | --- | --- | --- | --- | ------ | ---- | --- | --- | ------ | --- |
|     |     |     |     |     | (+X)   |      |     |     | Access |     |
Port
|     | List Item   |     |             |     | As Measured |             |     |             |     | Required |
| --- | ----------- | --- | ----------- | --- | ----------- | ----------- | --- | ----------- | --- | -------- |
|     | Width [x–y] |     | Side 1 (–Y) |     | Side 2 (–X) | Side 3 (+Y) |     | Side 4 (+X) |     |          |
+Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Middle ____________ ____________ ____________ ____________ 100 ± 0.1 mm
–Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Height [x–y] Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
____________ ____________ ____________ ____________ 170.2 ± 0.1 mm
|     |     | Rail 1 (+X, –Y)  |                |     | Rail 2 (–X, –Y)  | Rail 3 (–X, +Y)  |     | Rail 4 (+X, +Y)  |     |     |
| --- | --- | ---------------- | -------------- | --- | ---------------- | ---------------- | --- | ---------------- | --- | --- |
|     |     |                  | length x width |     | length x width   | length x width   |     | length x width   |     |     |
+Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
–Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
Protrusions Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X) Side 5 (–Z) Side 6 (+Z)
|     |     | _________ | _________ |     | _________ | _________ | _________ |     | _________ | ≤ 6.5 mm |
| --- | --- | --------- | --------- | --- | --------- | --------- | --------- | --- | --------- | -------- |
80 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative

CubeSat
101
Appendices
2U CubeSat Acceptance Checklist
| Project:         |     |     | Date/Time:      |     |     | Engineers: |                           |     |     |
| ---------------- | --- | --- | --------------- | --- | --- | ---------- | ------------------------- | --- | --- |
| Organization:    |     |     | Location:       |     |     |            |                           |     |     |
| Satellite Name:  |     |     | Satellite S/N:  |     |     |            | Revision Date: 02/20/2014 |     |     |
Mass (< 2.66 kg) _________________ RBF Pin (≤ 6.5 mm) _________________
| Spring Plungers  |     | Functional Y / N          |     |     | Rails Anodized |     |     | Y / N |     |
| ---------------- | --- | ------------------------- | --- | --- | -------------- | --- | --- | ----- | --- |
| (Depressed)      |     | Flush with Standoff Y / N |     |     |                |     |     |       |     |
Deployment Switches  Functional Y / N  Deployables Constrained Y / N
| (Depressed) |     | Flush with Standoff Y / N |     |     |     |     |     |     |     |
| ----------- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
Mark on the diagram the locations of the RBF pin, connectors, deployables, and any envelope violations.
Rail 3
(–X,+Y)
Authorized by:
|     |     | Side 3 |     |     |     |     |     |     | IT 1: _________ |
| --- | --- | ------ | --- | --- | --- | --- | --- | --- | --------------- |
(+Y)
Rail 4
|     | (+X,+Y) |     |     |     |     |     |     |     | IT 2: _________ |
| --- | ------- | --- | --- | --- | --- | --- | --- | --- | --------------- |
Side 5
|     |        |     |        | (–Z) |     |     |     |     | Passed: Y / N |
| --- | ------ | --- | ------ | ---- | --- | --- | --- | --- | ------------- |
|     | Access |     | Access |      |     |     |     |     |               |
|     | Port   |     | Port   |      |     |     |     |     |               |
Side 4
(+X)
Side 2
(–X)
|     |     |     |     | Access | Access |     |     |     |     |
| --- | --- | --- | --- | ------ | ------ | --- | --- | --- | --- |
|     |     |     |     | Port   | Port   |     |     |     |     |
Side 6
(+Z)
Rail 2
(–X,–Y)
Side 1
(–Y)
Rail 1
(+X,–Y)
| List Item   |     |             |             | As Measured |             |     |             |     | Required |
| ----------- | --- | ----------- | ----------- | ----------- | ----------- | --- | ----------- | --- | -------- |
| Width [x–y] |     | Side 1 (–Y) | Side 2 (–X) |             | Side 3 (+Y) |     | Side 4 (+X) |     |          |
+Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Middle ____________ ____________ ____________ ____________ 100 ± 0.1 mm
–Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Height [x–y] Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
____________ ____________ ____________ ____________ 227.0 ± 0.2 mm
|     | Rail 1 (+X, –Y)  |                | Rail 2 (–X, –Y)  |     | Rail 3 (–X, +Y)  |     | Rail 4 (+X, +Y)  |     |     |
| --- | ---------------- | -------------- | ---------------- | --- | ---------------- | --- | ---------------- | --- | --- |
|     |                  | length x width | length x width   |     | length x width   |     | length x width   |     |     |
+Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
–Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
Protrusions Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X) Side 5 (–Z) Side 6 (+Z)
|     | _________ | _________ |     | _________ | _________ | _________ |     | _________ | ≤ 6.5 mm |
| --- | --------- | --------- | --- | --------- | --------- | --------- | --- | --------- | -------- |
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative 81

CubeSat
101
Appendices
3U CubeSat Acceptance Checklist
| Project:         |     |     |     | Date/Time:      |     |     | Engineers: |                           |     |     |
| ---------------- | --- | --- | --- | --------------- | --- | --- | ---------- | ------------------------- | --- | --- |
| Organization:    |     |     |     | Location:       |     |     |            |                           |     |     |
| Satellite Name:  |     |     |     | Satellite S/N:  |     |     |            | Revision Date: 02/20/2014 |     |     |
Mass (< 4.00 kg) _________________ RBF Pin (≤ 6.5 mm) _________________
| Spring Plungers  |     |     | Functional Y / N          |     |     | Rails Anodized |     |     | Y / N |     |
| ---------------- | --- | --- | ------------------------- | --- | --- | -------------- | --- | --- | ----- | --- |
| (Depressed)      |     |     | Flush with Standoff Y / N |     |     |                |     |     |       |     |
Deployment Switches  Functional Y / N  Deployables Constrained Y / N
| (Depressed) |     |     | Flush with Standoff Y / N |     |     |     |     |     |     |     |
| ----------- | --- | --- | ------------------------- | --- | --- | --- | --- | --- | --- | --- |
Mark on the diagram the locations of the RBF pin, connectors, deployables, and any envelope violations.
Rail 3
(–X,+Y)
Authorized by:
|     |     |     |     | Side 3 |     |     |     |     |     | IT 1: _________ |
| --- | --- | --- | --- | ------ | --- | --- | --- | --- | --- | --------------- |
(+Y)
Rail 4
|     |     | (+X,+Y) |     |     |     |     |     |     |     | IT 2: _________ |
| --- | --- | ------- | --- | --- | --- | --- | --- | --- | --- | --------------- |
Side 5
|     |     |        |      |        |     |        | (–Z) |     |     | Passed: Y / N |
| --- | --- | ------ | ---- | ------ | --- | ------ | ---- | --- | --- | ------------- |
|     |     | Access |      | Access |     | Access |      |     |     |               |
|     |     |        | Port | Port   |     | Port   |      |     |     |               |
Side 4
(+X)
Side 2
(–X)
|     |     | Access |     | Access |     | Access |     |     |     |     |
| --- | --- | ------ | --- | ------ | --- | ------ | --- | --- | --- | --- |
|     |     | Port   |     | Port   |     | Port   |     |     |     |     |
Side 6
(+Z)
Rail 2
(–X,–Y)
Side 1
(–Y)
Rail 1
(+X,–Y)
|     | List Item   |     |             |     |             | As Measured |     |             |     | Required |
| --- | ----------- | --- | ----------- | --- | ----------- | ----------- | --- | ----------- | --- | -------- |
|     | Width [x–y] |     | Side 1 (–Y) |     | Side 2 (–X) | Side 3 (+Y) |     | Side 4 (+X) |     |          |
+Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Middle ____________ ____________ ____________ ____________ 100 ± 0.1 mm
–Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Height [x–y] Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
____________ ____________ ____________ ____________ 340.5 ± 0.3 mm
|     |     | Rail 1 (+X, –Y)  |                |     | Rail 2 (–X, –Y)  | Rail 3 (–X, +Y)  |     | Rail 4 (+X, +Y)  |     |     |
| --- | --- | ---------------- | -------------- | --- | ---------------- | ---------------- | --- | ---------------- | --- | --- |
|     |     |                  | length x width |     | length x width   | length x width   |     | length x width   |     |     |
+Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
–Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
Protrusions Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X) Side 5 (–Z) Side 6 (+Z)
|     |     | _________ | _________ |     | _________ | _________ | _________ |     | _________ | ≤ 6.5 mm |
| --- | --- | --------- | --------- | --- | --------- | --------- | --------- | --- | --------- | -------- |
82 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers  NASA CubeSat Launch Initiative

CubeSat
101
Appendices
3U+ CubeSat Acceptance Checklist
Project: Date/Time: Engineers:
Organization: Location:
Satellite Name: Satellite S/N: Revision Date: 02/20/2014
Mass (< 4.00 kg) _________________ RBF Pin (≤ 6.5 mm) _________________
Spring Plungers Functional Y / N Rails Anodized Y / N
(Depressed) Flush with Standoff Y / N
Deployment Switches Functional Y / N Deployables Constrained Y / N
(Depressed) Flush with Standoff Y / N
Mark on the diagram the locations of the RBF pin, connectors, deployables, and any envelope violations.
Rail 3
(–X,+Y)
Authorized by:
Side 3 IT 1: _________
(+Y)
Rail 4
(+X,+Y) IT 2: _________
Side 5
(–Z)
Passed: Y / N
Access Access Access
Port Port Port
Side 4
(+X)
Side 2
(–X)
3U+ Volume
Length (Z): ____ ≤ 36 mm
Access Access Access
Port Port Port Diameter: ____ ≤ 64 mm
Side 6 3U+ Centered: Y / N
(+Z)
Rail 2
(–X,–Y)
Side 1
(–Y)
Rail 1
(+X,–Y)
List Item As Measured Required
Width [x–y] Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X)
+Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Middle ____________ ____________ ____________ ____________ 100 ± 0.1 mm
–Z ____________ ____________ ____________ ____________ 100 ± 0.1 mm
Height [x–y] Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
____________ ____________ ____________ ____________ 340.5 ± 0.3 mm
Rail 1 (+X, –Y) Rail 2 (–X, –Y) Rail 3 (–X, +Y) Rail 4 (+X, +Y)
length x width length x width length x width length x width
+Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
–Z Standoffs ____ x ____ ____ x ____ ____ x ____ ____ x ____ ≥ 6.5 mm
Protrusions Side 1 (–Y) Side 2 (–X) Side 3 (+Y) Side 4 (+X) Side 5 (–Z) Side 6 (+Z)
_________ _________ _________ _________ _________ _________ ≤ 6.5 mm
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 83

CubeSat
101
Appendices
D Technical Reference Documents for
CubeSat Requirements
Range
Document Number Title
AFOSHSTD 48-9 Radio Frequency Radiation (RFR) Safety
Program
Air Force Occupational Safety and Health Standard
AFSPCMAN 91-710 Launch Vehicles, Payloads, and Ground Support
Systems Requirements
Air Force Space Command Manual
EWR 127-1 Range Safety Requirements, Range User
Handbook
Eastern and Western Range
NASA Standards and Specifications
Document Number Title
NASA-STD-6016 Standard Materials and Processes
NASA Technical Standards Program Requirements for Spacecraft
NASA-STD-8719.14A Process for Limiting Orbital Debris
NPR 8715.6A NASA Procedural Requirements for Limiting Orbital Debris
Generation
Standards and Specifications
Document Number Title
Air Force Memo Joint 45 SW/SE and 30 SW/SE Interim Policy Regarding EWR 127-1 Requirements
for System Safety for Flight and Aerospace Ground Equipment Lithium-Ion
4 May 2005
Batteries
GSFC-STD-7000 A General Environmental Verification Standard for GSFC Flight Programs and
Projects
MIL-STD-461F Electronic Emission and Susceptibility Requirements for the Control of
Electromagnetic Interference and Notices 1 and 2 dated 4/08/1986, 4/01/1987 and
10/15/1987 respectively
SMC-S-016 Space and Missile Systems Center Standard Test Requirements for Launch,
Upper-Stage, and Space Vehicles
UL 1642 UL Standard for Safety for Lithium Batteries
UL 2054 UL Standard for Safety for Household and Commercial Batteries
84 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

CubeSat
101
Appendices
E Notional Timeline of Events/Deliverables
Concept Development
Funding
Merit/Feasibility Reviews
Develop/Submit Proposal
CSLI Selection Process
Manifesting
Mission Coordination
Licensing
Document Development/
Submission
Ground Station Development
and Testing
Flight Hardware Fabrication
Readiness Reviews
Dispenser Integration
Launch Vehicle Integration
Launch and Mission Operations
Months
This notional timeline shows how these phases might come together for a project.
CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative 85

CubeSat
101
Cover Image Credits
Front Cover Back Cover
Top: Launch of NASA’s NPOESS Preparatory Project (NPP) Top: A set of CubeSats is photographed by an Expedition
mission on Oct. 28, 2011 which deployed five CubeSats as 38 crew member after the deployment by the NanoRacks
part of the Educational Launch of the Nanosatellite (ELaNa)-III Launcher attached to the end of the Japanese robotic arm
Mission. [U.S. Air Force/Staff Sgt. Andrew Satran] affixed to the Space Station. [NASA]
Left: Students Alex Diaz and Riki Munakata of California Left: Students Sergei Posnov, David Einhorn, Thompson
Polytechnic State University testing the LightSail CubeSat. Cragwell, and Maria Kromis working on the ANDESITE
LightSail is a citizen-funded technology demonstration mission CubeSat from Boston University. ANDESITE will measure
sponsored by the Planetary Society using solar propulsion for small-scale spatial magnetic features in the auroral current
CubeSats. [The Planetary Society] systems. The measurements will be made through a
constellation of picosatellites deployed by the main payload and
Middle: ChargerSat-1’s mission was developed by students communicating over a mesh network. [Boston University]
from the University of Alabama, Huntsville to conduct three
technology demonstrations: a gravity gradient stabilization Middle: The BisonSat mission is an Earth Science mission
system will passively stabilize the spacecraft; deployable solar that will demonstrate the acquisition of 100-meter or better
panels will nearly double the power input to the spacecraft; and resolution visible light imagery of Earth using passive magnetic
the same deployable solar panels will shape the gain pattern of stabilization from a CubeSat. BisonSat is the first CubeSat
a nadir-facing monopole antenna, allowing improved horizon- designed, built, tested, and operated by tribal college students.
to-horizon communications. [University of Alabama, Huntsville] Launched by NASA’s CubeSat Launch Initiative on the ELaNa
XII mission as an auxiliary payload aboard the NROL- 55
Right: CAPE-2 was developed by students from the University Mission on October 8, 2015. [Salish Kootenai College]
of Louisiana Lafayette to engage, inspire and educate K-12
students to encourage them to pursue STEM careers. The Right: University of Kentucky students Jason Rexroat and Alex
secondary focus is the technology demonstration of deployed Clements working on KySat-2 a technology demonstration
solar panels to support the following payloads: text to speech, CubeSat mission developed by students from the University
voice repeater, tweeting, email, file transfer and data collection of Kentucky in Lexington, Kentucky that builds upon KySat-1
from buoys. [University of Louisiana at Lafayette] by expanding the K-12 outreach goals to interest students to
science, technology, engineering and mathematics (STEM)
fields and space technology. It also will test components of a
novel attitude determination system called a Stellar Gyroscope
that uses sequences of digital pictures to determine the
three-axis rotation rate of the satellite. Launched by NASA’s
CubeSat Launch Initiative on the ELaNa IV mission as an
auxiliary payload aboard the U.S. Air Force- led Operationally
Responsive Space (ORS-3) Mission on November 19, 2013.
[University of Kentucky]
86 CubeSat 101: Basic Concepts and Processes for First-Time CubeSat Developers NASA CubeSat Launch Initiative

www.nasa.gov
NP-2017-10-2470-HQ