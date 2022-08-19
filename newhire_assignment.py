import pandas as pd
import numpy as np
import json
from pyomo.environ import *

class NewHireAssignment:
    def __init__(self, state_loc, state_stat_loc, planning_horizon=30, max_newhire_hrs=30, max_hires=5):
        self.states = None
        self.states_stat = None
        self.states_stat_post_hiring = None
        self.therapist_stat_post_hiring = None
        self.hiring_decision = None
        self.licensing_decision = None
        self.hiring_and_licensing_decision = None
        self.hireable_hours = None
        self._H = None
        self._S = None
        self.state_loc = state_loc
        self.state_stat_loc = state_stat_loc
        self.planning_horizon = planning_horizon
        self.max_newhire_hrs = max_newhire_hrs
        self.max_hires = max_hires

    def _load_input(self):
        self.states_stat = pd.read_csv(self.state_stat_loc, usecols=['State', 'assigned_new_license', 'deficit_per_week'])
        with open(self.state_loc) as f:
            self.states = json.load(f)

    def _set_hireable_hrs(self):
        self.hireable_hours = self.states_stat[['State', 'deficit_per_week']]\
            .groupby('State')\
            .apply(lambda x: 0 if self.states[x.name]['time_to_hire'] > self.planning_horizon
                                    else sum(x['deficit_per_week']))\
            .reset_index()
        self.hireable_hours.columns = ['State', 'hireable_hours']

    def _optimize_by_linear_ip(self):
        # set up model
        model = ConcreteModel() ## local pointer only for the purpose of setting constraint
        self.model = model
        self._S = self.states.keys()
        self._H = range(self.max_hires)
        # create decision variables
        self.model.Tsh = Var(self._S, self._H, domain=NonNegativeIntegers)
        self.model.Lsh = Var(self._S, self._H, domain=Binary)
        # define objective
        demand = sum(self.hireable_hours.loc[self.hireable_hours['State']==s, 'hireable_hours'].values[0] for s in self._S)
        supply = sum(sum(self.model.Tsh[s, h]*self.model.Lsh[s,h] for h in self._H) for s in self._S)
        self.model.OBJ = Objective(expr=demand - supply, sense=minimize)
        # constraints
        def newhire_constraint(model,h):
            return (0, sum(model.Tsh[s,h] for s in self._S), self.max_newhire_hrs)
        def state_constraint(model,s):
            return (0, sum(model.Tsh[s,h] for h in self._H), self.hireable_hours.loc[self.hireable_hours['State']==s, 'hireable_hours'].values[0])
        def licensing_constraint(model, s, h):
            upper_limit = 0 if self.states[s]['license_time'] > self.planning_horizon else 1
            return (0, model.Lsh[s,h], upper_limit)
        self.model.hiringConstraint = Constraint(self._H, rule=newhire_constraint)
        self.model.stateConstraint = Constraint(self._S, rule=state_constraint)
        self.model.licensingConstraint = Constraint(self._S, self._H, rule=licensing_constraint)
        opt = SolverFactory("bonmin", executable="./bonmin-osx/bonmin")
        opt.solve(self.model)

    def _generate_outputs(self):
        hire_decision_out = self.model.Tsh.extract_values()
        self.hiring_decision = pd.DataFrame(hire_decision_out.values(), index=hire_decision_out.keys())
        self.hiring_decision = self.hiring_decision.reset_index()
        self.hiring_decision.columns = ['State', "new_hire_id", "newhire_hours"]
        self.hiring_decision = self.hiring_decision.loc[self.hiring_decision.newhire_hours!=0]

        licensing_decision_out = self.model.Lsh.extract_values()
        self.licensing_decision = pd.DataFrame(licensing_decision_out.values(), index=licensing_decision_out.keys())
        self.licensing_decision = self.licensing_decision.reset_index()
        self.licensing_decision.columns = ['State', "new_hire_id", "newhire_licensing"]

        self.hiring_and_licensing_decision = pd.merge(self.hiring_decision,
                                                      self.licensing_decision,
                                                      how='left',
                                                      left_on=['State', 'new_hire_id'],
                                                      right_on=['State', 'new_hire_id'])

        hiring_decision_state_agg = self.hiring_decision.groupby('State')\
            .agg({'new_hire_id': 'count', 'newhire_hours': 'sum'})\
            .reset_index()
        hiring_decision_state_agg.columns = ['State', 'new_hires_count', 'newhire_hours']
        self.states_stat_post_hiring = pd.merge(self.states_stat, hiring_decision_state_agg, how='left', left_on='State', right_on='State')
        self.states_stat_post_hiring['deficit_post_hiring'] = self.states_stat_post_hiring['deficit_per_week'] - self.states_stat_post_hiring['newhire_hours']
        self.states_stat_post_hiring['deficit_post_hiring'] = self.states_stat_post_hiring['deficit_post_hiring'].fillna(self.states_stat_post_hiring['deficit_per_week'])
        # therapist stat post hiring
        self.therapist_stat_post_hiring = self.hiring_decision.groupby('new_hire_id')\
            .agg({'State': 'count', 'newhire_hours': 'sum'})\
            .reset_index()
        self.therapist_stat_post_hiring.columns = ['new_hire_id', 'states_eligible', 'newhire_hours']


    def _export_outputs(self):
        # export outputs
        self.hiring_and_licensing_decision.to_csv("./output/with_new_hire/new_hires_by_state.csv", index=False)
        self.states_stat_post_hiring.to_csv("./output/with_new_hire/states_state_post_hiring.csv")
        self.therapist_stat_post_hiring.to_csv("./output/with_new_hire/therapist_stat_post_hiring.csv")

    def plan(self):
        self._load_input()
        self._set_hireable_hrs()
        self._optimize_by_linear_ip()
        self._generate_outputs()
        self._export_outputs()