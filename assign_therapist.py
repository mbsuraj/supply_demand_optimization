import pandas as pd
import numpy as np
import json
from pyomo.environ import *
from pyomo.kernel import Binary


class AssignTherapist:
    def __init__(self, therapist_loc, state_loc, therapist_state_loc, planning_horizon=30, simulation_count=30):
        self.therapists = None
        self.states = None
        self.therapist_state_license = None
        self.model = None
        self._P = None
        self._S = None
        self.therapist_assignment = None
        self.state_stats = None
        self.therapist_stats = None
        self.therapist_loc = therapist_loc
        self.state_loc = state_loc
        self.therapist_state_loc = therapist_state_loc
        self.planning_horizon = planning_horizon
        self.simulation_count = simulation_count

    def _load_input(self):
        with open(self.therapist_loc) as f:
            self.therapists = json.load(f)
        with open(self.state_loc) as f:
            self.states = json.load(f)
        with open(self.therapist_state_loc) as f:
            self.therapist_state_license = json.load(f)

    def _optimize_by_non_linear_ip(self):
        # set up model
        model = ConcreteModel() ## local pointer only for the purpose of setting constraint
        self.model = model
        self._P = self.therapists.keys()
        self._S = self.states.keys()
        # create decision variables
        self.model.Tps = Var(self._P, self._S, domain=NonNegativeIntegers)
        self.model.Lps = Var(self._P, self._S, domain=Binary)
        demand = sum(self.states[s]['demand_per_week'] for s in self._S)
        assigned_supply = sum(sum(self.model.Tps[p, s] * self._get_assignment(p, s) for s in self._S) for p in self._P)
        licensed_supply = sum(sum(self.model.Tps[p, s] * self.model.Lps[p, s] for s in self._S) for p in self._P)
        assigned_licensed_supply = sum(sum(self.model.Tps[p, s] * self.model.Lps[p, s] * self._get_assignment(p, s) for s in self._S) for p in self._P)
        supply = (assigned_supply + licensed_supply - assigned_licensed_supply)
        self.model.OBJ = Objective(expr=demand - supply, sense=minimize)
        # constraints
        def therapist_constraint(model, p):
            return (0, sum(model.Tps[p, s] for s in self._S), self.therapists[p]['h_per_week'])

        def state_constraint(model, s):
            return (0, sum(model.Tps[p, s] for p in self._P), self.states[s]['demand_per_week'])

        def licensing_constraint(model, p, s):
            upper_bound = 0 if (s in self.therapist_state_license[p]) and (self.states[s]['license_time'] > self.planning_horizon) else 1
            return (0, model.Lps[p, s], upper_bound)
        self.model.therapistConstraint = Constraint(self._P, rule=therapist_constraint)
        self.model.stateConstraint = Constraint(self._S, rule=state_constraint)
        self.model.licensingConstraint = Constraint(self._P, self._S, rule=licensing_constraint)
        opt = SolverFactory("bonmin", executable="./bonmin-osx/bonmin")
        opt.solve(self.model)

    def _generate_outputs(self):
        time_decision_out = self.model.Tps.extract_values()
        license_decision_out = self.model.Lps.extract_values()
        therapist_time_assignment = pd.DataFrame(time_decision_out.values(), index=time_decision_out.keys())
        therapist_license_assignment = pd.DataFrame(license_decision_out.values(), index=license_decision_out.keys())
        self.therapist_assignment = pd.merge(therapist_time_assignment, therapist_license_assignment, left_index=True,
                                        right_index=True, how='left')
        self.therapist_assignment = self.therapist_assignment.reset_index()
        self.therapist_assignment.columns = ['Therapist', 'State', "assigned_hrs_per_week", "assigned_new_license"]
        # state level stats
        self.state_stats = self.therapist_assignment[['State', 'assigned_hrs_per_week', 'assigned_new_license']] \
            .groupby('State') \
            .aggregate({'assigned_hrs_per_week': 'sum',
                        'assigned_new_license': 'sum'}) \
            .reset_index()
        self.state_stats['demand_per_week'] = self.state_stats.apply(lambda x: self.states[x['State']]['demand_per_week'], axis=1)
        self.state_stats['deficit_per_week'] = self.state_stats.apply(lambda x: x['demand_per_week'] - x['assigned_hrs_per_week'],
                                                            axis=1)
        # Therapist level stats
        self.therapist_stats = self.therapist_assignment[['Therapist', "assigned_hrs_per_week", "assigned_new_license"]] \
            .groupby('Therapist') \
            .aggregate({'assigned_hrs_per_week': 'sum',
                        'assigned_new_license': 'sum'}) \
            .reset_index()
        self.therapist_stats['initial_available_hrs_per_week'] = self.therapist_stats.apply(
            lambda x: self.therapists[x['Therapist']]['h_per_week'], axis=1)
        self.therapist_stats['final_available_hrs_per_week'] = self.therapist_stats.apply(
            lambda x: x['initial_available_hrs_per_week'] - x['assigned_hrs_per_week'], axis=1)

    def _export_outputs(self):
        # export outputs
        self.therapist_assignment.to_csv("./output/with_existing_resource/therapist_assignment.csv", index=False)
        self.state_stats.to_csv("./output/with_existing_resource/state_stats.csv", index=False)
        self.therapist_stats.to_csv("./output/with_existing_resource/therapist_stats.csv", index=False)

    def _get_assignment(self, p, s):
        if s in self.therapist_state_license[p]:
            return 1
        else:
            return 0
    def _generate_demand_from_dist(self):
        for s in self.states.keys():
            self.states[s]['demand_per_week'] = np.ceil(
                np.random.normal(self.states[s]['demand_dist_mean'], self.states[s]['demand_dist_std']))

    def simulate(self):
        for i in range(self.simulation_count):
            self._load_input()
            self._generate_demand_from_dist()
            self._optimize_by_non_linear_ip()
            self._generate_outputs()
            self._export_outputs()



