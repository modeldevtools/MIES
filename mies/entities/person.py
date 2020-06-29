import numpy as np
import pandas as pd
import plotly.graph_objects as go

from plotly.offline import plot

from econtools.budget import Good, Budget
from econtools.slutsky import Slutsky
from econtools.utility import CobbDouglas
from parameters import INITIAL_PREMIUM
from utilities.queries import query_person, query_policy, query_policy_history


class Person:
    def __init__(
        self,
        person_id
    ):
        self.id = person_id

        self.data = query_person(self.id)
        self.income = self.data['income'].loc[0]

        self.utility = CobbDouglas(
            c=self.data['cobb_c'].loc[0],
            d=self.data['cobb_d'].loc[0]
        )

        self.policy_history = None
        self.policy = None
        self.budget = None
        self.premium = None
        self.optimal_bundle = None
        self.consumption_figure = None
        self.offer = None
        self.engel = None
        self.demand = None
        self.slutsky = None

    def get_policy_history(self):
        self.policy_history = query_policy_history(self.id)

    def get_policy(
        self,
        company_name,
        policy_id
    ):
        self.policy = query_policy(company_name, policy_id)
        self.premium = self.policy['premium'].loc[0]

    def get_budget(self):
        all_other = Good(1, name='All Other Goods')
        if self.policy is None:
            insurance = Good(INITIAL_PREMIUM, name='Insurance')
            self.premium = INITIAL_PREMIUM
        else:
            insurance = Good(self.premium, name='Insurance')
        self.budget = Budget(insurance, all_other, income=self.income, name='Budget')

    def get_consumption(self):
        self.optimal_bundle = self.utility.optimal_bundle(
            p1=self.premium,
            p2=1,
            m=self.income
        )

    def get_consumption_figure(self):
        fig = go.Figure()
        fig.add_trace(self.budget.get_line())
        fig.add_trace(self.utility.trace(k=self.optimal_bundle[2], m=self.income / self.premium * 1.5))
        fig.add_trace(self.utility.trace(k=self.optimal_bundle[2] * 1.5, m=self.income / self.premium * 1.5))
        fig.add_trace(self.utility.trace(k=self.optimal_bundle[2] * .5, m=self.income / self.premium * 1.5))

        fig['layout'].update({
            'title': 'Consumption for Person ' + str(self.id),
            'title_x': 0.5,
            'xaxis': {
                'title': 'Amount of Insurance',
                'range': [0, self.income / self.premium * 1.5]
            },
            'yaxis': {
                'title': 'Amount of All Other Goods',
                'range': [0, self.income * 1.5]
            }
        })
        self.consumption_figure = fig
        return fig

    def get_offer(self):
        # only works for Cobb Douglas right now
        def o(m):
            return self.utility.optimal_bundle(
                p1=self.premium,
                p2=1,
                m=m
            )

        self.offer = o

    def get_engel(self):
        # only works for Cobb Douglas right now

        def e(m):
            return self.utility.optimal_bundle(
                p1=self.premium,
                p2=1,
                m=m
            )[0]

        self.engel = e

    def get_demand(self):
        # only works for Cobb Douglas right now

        def d(p):
            return self.utility.optimal_bundle(
                p1=p,
                p2=1,
                m=self.income
            )[0]

        self.demand = d

    def show_consumption(self):
        plot(self.consumption_figure)

    def show_offer(self):
        offer_frame = pd.DataFrame(columns=['income'])
        offer_frame['income'] = np.arange(0, self.income * 2, 1000)
        offer_frame['x1'], offer_frame['x2'] = self.offer(offer_frame['income'])[:2]

        offer_trace = {
            'x': offer_frame['x1'],
            'y': offer_frame['x2'],
            'mode': 'lines',
            'name': 'Offer Curve'
        }

        fig = self.consumption_figure
        fig.add_trace(offer_trace)
        plot(fig)
        return fig

    def show_engel(self):
        engel_frame = pd.DataFrame(columns=['income'])
        engel_frame['income'] = np.arange(0, self.income * 2, 1000)
        engel_frame['x1'] = engel_frame['income'].apply(self.engel)

        engel_trace = {
            'x': engel_frame['x1'],
            'y': engel_frame['income'],
            'mode': 'lines',
            'name': 'Engel Curve'
        }

        fig = go.Figure()
        fig.add_trace(engel_trace)

        fig['layout'].update({
            'title': 'Engel Curve for Person ' + str(self.id),
            'title_x': 0.5,
            'xaxis': {
                'title': 'Amount of Insurance'
            },
            'yaxis': {
                'title': 'Income'
            }
        })

        plot(fig)
        return fig

    def show_demand(self):
        demand_frame = pd.DataFrame(columns=['price'])
        demand_frame['price'] = np.arange(self.premium/100, self.premium * 2, self.premium/100)
        demand_frame['x1'] = demand_frame['price'].apply(self.demand)

        demand_trace = {
            'x': demand_frame['x1'],
            'y': demand_frame['price'],
            'mode': 'lines',
            'name': 'Demand Curve'
        }

        fig = go.Figure()
        fig.add_trace(demand_trace)

        fig['layout'].update({
            'title': 'Demand Curve for Person ' + str(self.id),
            'title_x': 0.5,
            'xaxis': {
                'range': [0, self.income / self.premium * 2],
                'title': 'Amount of Insurance'
            },
            'yaxis': {
                'title': 'Premium'
            }
        })

        plot(fig)
        return fig

    def calculate_slutsky(self, new_budget):
        self.slutsky = Slutsky(
            old_budget=self.budget,
            new_budget=new_budget,
            utility_function=self.utility
        )
        self.slutsky.plot['layout'].update({
            'title': 'Slutsky Decomposition for Person ' + str(self.id)
        })
        self.slutsky.plot['layout'].update({'title_x': 0.5})
