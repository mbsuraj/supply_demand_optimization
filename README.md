# supply_demand_optimization
Run main.py script - it will trigger optimization in following stages

### First stage Optimization- Existing Therapists Assignment  
Objective - Minimize difference between demand and supply with the existing resources.  

Variables - 
1. Tps (Time per practitioner and state), NonNegativeInteger
2. Lps (new license assignment per practitioner and state) - Binary  

Constraints - 
1. Therapist constraint - (p)∑Tps  <= availability_per_therapist
2. State constraint - (s)∑Tps <= demand_per_state
3. Licensing constraint - Lps - {0, 1} if p didn’t have license in s before and p’s license_time < planning_horizon  

Definitions    
1. p- {set of all available therapists, P} 
2. s- {set of all states with practice, S} 

### Second Stage Optimization - New Hire Assignment
Objective - Minimize the supply deficit  with the new resources.

Variables - 
1. Tsh (Time per new hire and state), 
2. Lsh (license assignment per new hire  and state)

Constraints - 
1. New hire constraint - (h)∑Tsh  <= maximum_newhire_hrs
2. State constraint - (s)∑Tsh <= supply_deficit_per_state
3. Licensing constraint - Lps - {0, 1} if h’s license_time < planning_horizon

Definitions - 
1. h- {set id of all new potential hires, H} 
2. s- {set of all states with practice, S}



