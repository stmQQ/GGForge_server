from app.models import *
from app.extensions import db
from datetime import datetime
import math
from sqlalchemy.orm import joinedload


def make_group_stage(tournament_id, num_groups, qual_to_winners, qual_to_losers):
    tournament: Tournament = Tournament.query.options(
        joinedload(Tournament.participants),
        joinedload(Tournament.teams)
    ).get(tournament_id)

    if not tournament:
        return None

    group_stage: GroupStage = GroupStage(
        tournament_id=tournament_id, winners_bracket_qualified=qual_to_winners, losers_bracket_qualified=qual_to_losers)

    db.session.add(group_stage)
    db.session.flush()

    if tournament.type == 'team':
        entities = tournament.teams
    else:
        entities = tournament.participants

    total = len(entities)

    if total == 0:
        return None

    group_size = math.ceil(total / num_groups)

    chunks = [entities[i: i + group_size] for i in range(0, total, group_size)]

    for i, group_entities in enumerate(chunks):
        letter = chr(65 + i)
        group = make_group(groupstage_id=group_stage.id, participants=group_entities,
                           max_participants=len(group_entities), letter=letter)
        group_stage.groups.append(group)

    db.session.commit()

    return group_stage


def make_group(groupstage_id, participants, max_participants, letter):
    group = Group(groupstage_id=groupstage_id,
                  max_participants=max_participants, letter=letter)

    db.session.add(group)
    db.session.flush()

    if isinstance(participants[0], User):
        group.participants.extend(participants)
        for p in group.participants:
            row = GroupRow(place=0, group=group, user=p)
            db.session.add(row)
    else:
        group.teams.extend(participants)
        for t in group.teams:
            row = GroupRow(place=0, group=group, team=t)
            db.session.add(row)

    return group
