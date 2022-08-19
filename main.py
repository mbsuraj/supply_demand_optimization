from assign_therapist import AssignTherapist
from newhire_assignment import NewHireAssignment

def run_therapist_assignment():
    # Use a breakpoint in the code line below to debug your script.
    therapist_loc = "./input/therapists.json"
    state_loc = "./input/states.json"
    therapist_state_loc = './input/therapist_state_license.json'
    planning_horizon = 45
    simulation_count = 1
    assignment_obj = AssignTherapist(therapist_loc=therapist_loc,
                                     state_loc=state_loc,
                                     therapist_state_loc=therapist_state_loc,
                                     planning_horizon=planning_horizon,
                                     simulation_count=simulation_count
                                     )
    assignment_obj.simulate()

    state_stat_loc = './output/with_existing_resource/state_stats.csv'
    max_newhire_hrs = 30
    max_hires = 3
    new_hire_obj = NewHireAssignment(state_loc=state_loc,
                                     state_stat_loc=state_stat_loc,
                                     planning_horizon=planning_horizon,
                                     max_newhire_hrs=max_newhire_hrs,
                                     max_hires=max_hires
                                     )
    new_hire_obj.plan()

if __name__ == '__main__':
    run_therapist_assignment()
