# -*- coding: utf-8 -*-
"""
xG chain
===========================
Calculate xG chain
"""
#TODO - possesion chain separate chains + plots for possesion chains 
#Voronoi goals - goal from the distance - both 2 teams and attacking team  - different file
#importing necessary libraries 
 

##############################################################################
# Preparing variables for models
# ----------------------------
#
# For our models we will use all non-linear combinations of the starting and ending
# x coordinate and *c* - distance from the middle of the pitch. First, we filter ones
# where only starting coordinate were saved, then we create separate columns for *x* and *c*
# start and end. We assign value 105 to shot x_1 and 0 for c_1. Then, we create combinations
# with replacement of these variables - to get their non-linear transfomations. As the next step,
# we multiply the columns in the combination and create a model with them. 


#model variables
var = ["x0", "x1", "c0", "c1"]

#combinations
from itertools import combinations_with_replacement
inputs = []
inputs.extend(combinations_with_replacement(var, 1))
inputs.extend(combinations_with_replacement(var, 2))
inputs.extend(combinations_with_replacement(var, 3))

#make new columns
for i in inputs:
    if len(i) > 1:
        column = ''
        x = 1
        for c in i:
            column += c
            x = x*df[c]
        df[column] = x
        var.append(column)

#make model for smf library
model = ''
for v in var[:-1]:
    model = model  + v + ' + '
model = model + var[-1]


##############################################################################
# Building models
# ----------------------------
#
# Now we can build models. First we create a logistic regression predicting if
# there was a shot in the end of the chain. Then, we build a linear regression 
# xG~model. 

#logistic regression
passes = df.loc[ df["eventName"].isin(["Pass"])]
passes["shot_end"] = passes["shot_end"].astype(object)
shot_model = smf.glm(formula="shot_end ~ " + model, data=passes,
                           family=sm.families.Binomial()).fit()
print(shot_model.summary())
b_log = shot_model.params

#OLS
goal_model = smf.ols(formula='xG ~ ' + model, data=shot_ended).fit()
print(goal_model.summary())
b_lin = goal_model.params

##############################################################################
# Calculating xGchain values for events
# ----------------------------
#
# As the next step we calculate the xGchain value for action son the pitch. To do so, we
# multiply probability of the shot with goal probability. 

def calculate_xGChain(sh):
    bsum = b_log[0]
    for i,v in enumerate(var):
        bsum = bsum+b_log[i+1]*sh[v]
    p_shot = 1/(1+np.exp(bsum))
   
    bsum=b_lin[0]
    for i,v in enumerate(var):
       bsum=bsum+b_lin[i+1]*sh[v]
    p_goal = bsum
    return p_shot*p_goal

xGchain = shot_ended.apply(calculate_xGChain, axis=1)
shot_ended = shot_ended.assign(xGchain=xGchain)

##############################################################################
# Finding out players with highest xGchain
# ----------------------------
# As the last step we want to find out which players who played more than 400 minutes
# scored the best in possesion-adjusted xGchain per 90. We repeat steps that you already know 
# from `Radar Plots <https://soccermatics.readthedocs.io/en/latest/gallery/lesson3/plot_RadarPlot.html>`_.
# We group them by player, sum, assign merge it with players database to keep players name,
# adjust per possesion and per 90. Only the last step differs, since we stored *percentage_df*
# in a .json file that can be found `here <https://github.com/soccermatics/Soccermatics/tree/main/course/lessons/minutes_played>`_.

summary = shot_ended[["playerId", "xGchain"]].groupby(["playerId"]).sum().reset_index()

path = os.path.join(str(pathlib.Path().resolve().parents[0]),"data", 'Wyscout', 'players.json')
player_df = pd.read_json(path, encoding='unicode-escape')
player_df.rename(columns = {'wyId':'playerId'}, inplace=True)
player_df["role"] = player_df.apply(lambda x: x.role["name"], axis = 1)
to_merge = player_df[['playerId', 'shortName', 'role']]

summary = summary.merge(to_merge, how = "left", on = ["playerId"])


path = os.path.join(str(pathlib.Path().resolve().parents[0]),"minutes_played", 'minutes_played_per_game_England.json')
with open(path) as f:
    minutes_per_game = json.load(f)
#filtering over 400 per game
minutes_per_game = pd.DataFrame(minutes_per_game)
minutes = minutes_per_game.groupby(["playerId"]).minutesPlayed.sum().reset_index()
summary = minutes.merge(summary, how = "left", on = ["playerId"])
summary = summary.fillna(0)
summary = summary.loc[summary["minutesPlayed"] > 400]
#calculating per 90
summary["xGchain_p90"] = summary["xGchain"]*90/summary["minutesPlayed"]




#adjusting for possesion
path = os.path.join(str(pathlib.Path().resolve().parents[0]),"minutes_played", 'player_possesion_England.json')
with open(path) as f:
    percentage_df = json.load(f)
percentage_df = pd.DataFrame(percentage_df)
#merge it
summary = summary.merge(percentage_df, how = "left", on = ["playerId"])

summary["xGchain_adjusted_per_90"] = (summary["xGchain"]/summary["possesion"])*90/summary["minutesPlayed"]
summary[['shortName', 'xGchain_adjusted_per_90']].sort_values(by='xGchain_adjusted_per_90', ascending=False).head(5)

##############################################################################
# Challenge
# ----------------------------
# 1. StatsBomb has recently released a dataset with Indian Superleague 2021/22 games. Calculate
# xGchain values for these player. Note that the possesion chains are already isolated. Which player stood out the most? 











