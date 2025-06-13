from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models import Tournament, User, Game, GroupStage, PlayoffStage, PrizeTable, Match, Map, Group, PlayoffStageMatch, Team, PrizeTableRow, GroupRow, ScheduledTournament
from datetime import datetime, UTC
import math
import random
import uuid


def get_tournaments_by_game(game_id: UUID):
    """
    Retrieve all tournaments for a specific game.

    Args:
        game_id: The UUID of the game.

    Returns:
        list: List of Tournament objects.

    Raises:
        ValueError: If the game is not found.
    """
    game = Game.query.get(game_id)
    if not game:
        raise ValueError("Game not found")
    return Tournament.query.filter_by(game_id=game_id).all()


def get_tournaments_by_participant(user_id: UUID):
    """
    Retrieve all tournaments where the user is a participant.

    Args:
        user_id: The UUID of the user.

    Returns:
        list: List of Tournament objects.

    Raises:
        ValueError: If the user is not found.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    return user.participated_tournaments


def get_tournaments_by_creator(user_id: UUID):
    """
    Retrieve all tournaments created by the user.

    Args:
        user_id: The UUID of the user.

    Returns:
        list: List of Tournament objects.

    Raises:
        ValueError: If the user is not found.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    return user.created_tournaments


def get_tournament(tournament_id: UUID):
    """
    Retrieve a specific tournament by ID.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        Tournament: The tournament object.

    Raises:
        ValueError: If the tournament is not found.
    """
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        raise ValueError("Tournament not found")
    return tournament


def get_tournament_group_stage(tournament_id: UUID):
    """
    Retrieve the group stage of a tournament.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        GroupStage: The group stage object, or None if not found.

    Raises:
        ValueError: If the tournament is not found.
    """
    tournament = get_tournament(tournament_id)
    return tournament.group_stage


def get_tournament_playoff_stage(tournament_id: UUID):
    """
    Retrieve the playoff stage of a tournament, with matches sorted by round_number.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        PlayoffStage: The playoff stage object, or None if not found.

    Raises:
        ValueError: If tournament or playoff stage is not found.
    """
    tournament = get_tournament(tournament_id)
    playoff_stage = tournament.playoff_stage
    if not playoff_stage:
        raise ValueError("Playoff stage not found")
    playoff_stage = PlayoffStage.query.options(
        joinedload(PlayoffStage.playoff_matches).joinedload(
            PlayoffStageMatch.match)
    ).filter_by(id=playoff_stage.id).first()
    if playoff_stage and playoff_stage.playoff_matches:
        playoff_stage.playoff_matches.sort(key=lambda x: int(x.round_number))
    return playoff_stage


def get_tournament_prize_table(tournament_id: UUID):
    """
    Retrieve the prize table of a tournament.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        PrizeTable: The prize table object, or None if not found.

    Raises:
        ValueError: If the tournament is not found.
    """
    tournament = get_tournament(tournament_id)
    return tournament.prize_table


def get_group_stage_matches(tournament_id: UUID):
    """
    Retrieve all matches in the group stage of a tournament.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        list: List of Match objects from the group stage.

    Raises:
        ValueError: If tournament or group stage is not found.
    """
    tournament = get_tournament(tournament_id)
    group_stage = tournament.group_stage
    if not group_stage:
        raise ValueError("Group stage not found")
    group_stage = GroupStage.query.options(
        joinedload(GroupStage.groups).joinedload(Group.matches)
    ).get(group_stage.id)
    matches = []
    for group in group_stage.groups:
        matches.extend(group.matches)
    return matches


def get_playoff_stage_matches(tournament_id: UUID):
    """
    Retrieve all matches in the playoff stage of a tournament.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        list: List of Match objects from the playoff stage.

    Raises:
        ValueError: If tournament or playoff stage is not found.
    """
    tournament = get_tournament(tournament_id)
    playoff_stage = tournament.playoff_stage
    if not playoff_stage:
        raise ValueError("Playoff stage not found")
    playoff_stage = PlayoffStage.query.options(
        joinedload(PlayoffStage.playoff_matches).joinedload(
            PlayoffStageMatch.match)
    ).get(playoff_stage.id)
    matches = [pm.match for pm in sorted(
        playoff_stage.playoff_matches, key=lambda x: int(x.round_number)) if pm.match]
    return matches


def get_all_tournament_matches(tournament_id: UUID):
    """
    Retrieve all matches in a tournament (group and playoff stages).

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        list: List of Match objects.

    Raises:
        ValueError: If the tournament is not found.
    """
    tournament = get_tournament(tournament_id)
    tournament = Tournament.query.options(
        joinedload(Tournament.matches)).get(tournament_id)
    return tournament.matches


def get_match(tournament_id: UUID, match_id: UUID):
    """
    Retrieve a specific match by ID, ensuring it belongs to the tournament.

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.

    Returns:
        Match: The match object.

    Raises:
        ValueError: If match is not found or doesn't belong to the tournament.
    """
    match = Match.query.get(match_id)
    if not match:
        raise ValueError("Match not found")
    if match.tournament_id != tournament_id:
        raise ValueError("Match does not belong to this tournament")
    return match


def create_tournament(
    title: str,
    game_id: UUID,
    creator_id: UUID,
    start_time: datetime,
    max_participants: int = 32,
    prize_fund: float = None,
    description: str = None,
    contact: str = None,
    status: str = "setup",
    has_group_stage: bool = False,
    has_playoff: bool = True,
    num_groups: int = None,
    max_participants_per_group: int = None,
    playoff_participants_count_per_group: int = 8,
    format_: str = 'bo1',
    final_format_: str = 'bo3'
) -> Tournament:
    """
    Create a new tournament with automatic generation of group stage, playoff stage, and prize table.

    Args:
        title: Tournament title.
        game_id: UUID of the game.
        creator_id: UUID of the creator (User).
        start_time: Tournament start time (datetime in UTC).
        type_: Tournament type ('solo' or 'team').
        max_participants: Maximum participants (default: 32).
        prize_fund: Total prize fund (optional).
        status: Initial status ('setup' by default).
        has_group_stage: Whether to create a group stage.
        has_playoff: Whether to create a playoff stage.
        num_groups: Number of groups (required if has_group_stage=True).
        max_participants_per_group: Max participants per group (required if has_group_stage=True).
        playoff_participants_count_per_group: Number of participants advancing to playoff (required if has_group_stage=True).

    Returns:
        Tournament: The created tournament object.

    Raises:
        ValueError: If parameters are invalid or database constraints fail.
    """
    # Validate game and creator
    game = Game.query.get(game_id)
    if not game:
        raise ValueError("Game not found")

    creator = User.query.get(creator_id)
    if not creator:
        raise ValueError("Creator not found")

    if max_participants < 2:
        raise ValueError("Tournament must allow at least 2 participants")

    if status not in ["open", "active", "completed", "cancelled"]:
        raise ValueError("Invalid tournament status")

    if has_group_stage:
        if not all([num_groups, max_participants_per_group, playoff_participants_count_per_group]):
            raise ValueError(
                "num_groups, max_participants_per_group, and playoff_participants_count_per_group "
                "are required for group stage tournaments"
            )
        if num_groups < 1 or max_participants_per_group < 2:
            raise ValueError(
                "Invalid number of groups or participants per group")
        if max_participants < num_groups * 2:
            raise ValueError(
                "max_participants too low for the number of groups")
        if playoff_participants_count_per_group < 2 or playoff_participants_count_per_group > num_groups * max_participants_per_group:
            raise ValueError("Invalid playoff_participants_count_per_group")

    if prize_fund is not None and prize_fund < 0:
        raise ValueError("Prize fund cannot be negative")

    # Create the tournament
    tournament = Tournament(
        id=uuid.uuid4(),
        title=title,
        game_id=game_id,
        creator_id=creator_id,
        start_time=start_time,
        max_players=max_participants,
        prize_fund=str(prize_fund) if prize_fund is not None else "0",
        type=game.type,
        status=status,
        match_format=format_,
        final_format=final_format_,
        description=description,
        contact=contact
    )

    try:
        db.session.add(tournament)
        db.session.flush()  # Get tournament.id
        # Create prize table (always)
        tournament.prize_table = create_prizetable(tournament.id)
        # Add default prize rows if prize_fund is set
        if prize_fund and prize_fund > 0:
            prize_distribution = [
                {"place": 1, "prize": prize_fund * 0.5},
                {"place": 2, "prize": prize_fund * 0.3},
                {"place": 3, "prize": prize_fund * 0.2}
            ]
            for prize in prize_distribution:
                create_prizetable_row(
                    tournament_id=tournament.id,
                    place=prize["place"],
                    prize=prize["prize"]
                )
        # Create group stage if enabled
        if has_group_stage:
            group_participants = [None] * max_participants
            group_stage = make_group_stage(
                tournament_id=tournament.id,
                num_groups=num_groups,
                max_participants_per_group=max_participants_per_group,
                participants=group_participants,
                winners_bracket_qualified=playoff_participants_count_per_group
            )
            tournament.group_stage = group_stage
            create_group_stage_matches(
                tournament.id, participants=group_participants, format_=tournament.match_format)
        # Create playoff stage if enabled
        if has_playoff:
            match_start_idx = 1
            if has_group_stage:
                playoff_participants_count_per_group = num_groups * \
                    group_stage.winners_bracket_qualified
                match_start_idx = int(num_groups * max_participants_per_group *
                                      (max_participants_per_group - 1) / 2 + 1)
            else:
                playoff_participants_count_per_group = max_participants
            winner_bracket_participants = [
                None] * playoff_participants_count_per_group
            playoff_stage = generate_single_elimination_bracket(
                tournament_id=tournament.id,
                participants=winner_bracket_participants,
                match_start_idx=match_start_idx
            )
            tournament.playoff_stage = playoff_stage
        # Schedule tournament start
        if status == "open":
            from app.apscheduler_tasks import schedule_tournament_start
            job_id = f"tournament_start_{tournament.id}"
            schedule_tournament_start(tournament.id, start_time, job_id)
            # Сохраняем запись о запланированном турнире
            scheduled = ScheduledTournament(
                tournament_id=tournament.id,
                start_time=start_time,
                job_id=job_id
            )
        db.session.add(scheduled)
        db.session.commit()
        return tournament

    except IntegrityError as e:
        db.session.rollback()
        raise ValueError(f"Failed to create tournament: {str(e)}")
    except ValueError as e:
        db.session.rollback()
        raise e


def create_match(tournament_id: UUID, participant1_id: UUID = None, participant2_id: UUID = None, group_id: UUID = None, playoff_match_id: UUID = None, type: str = None, format: str = "bo1", number: int = 1):
    """
    Create a new match in a tournament.

    Args:
        tournament_id: The UUID of the tournament.
        participant1_id: The UUID of the first participant (User or Team).
        participant2_id: The UUID of the second participant (User or Team).
        group_id: The UUID of the group (for group stage matches).
        playoff_match_id: The UUID of the playoff match (for playoff stage matches).
        type: The match type (e.g., 'group', 'playoff').
        format: The match format (e.g., 'bo1', 'bo3').

    Returns:
        Match: The created match object.

    Raises:
        ValueError: If tournament, group, or playoff match is not found, or invalid participants.
    """
    tournament = get_tournament(tournament_id)
    playoff_match = None

    if group_id and playoff_match_id:
        raise ValueError(
            "Match cannot belong to both group and playoff stages")

    if group_id:
        group = Group.query.get(group_id)
        if not group:
            raise ValueError("Group not found")
        if group.group_stage.tournament_id != tournament_id:
            raise ValueError("Group does not belong to this tournament")

    if playoff_match_id:
        playoff_match = PlayoffStageMatch.query.get(playoff_match_id)
        if not playoff_match:
            raise ValueError("Playoff match not found")
        if playoff_match.playoff_stage.tournament_id != tournament_id:
            raise ValueError(
                "Playoff match does not belong to this tournament")

    if participant1_id:
        participant1 = User.query.get(
            participant1_id) or Team.query.get(participant1_id)
        if not participant1:
            raise ValueError("Participant 1 not found")
    if participant2_id:
        participant2 = User.query.get(
            participant2_id) or Team.query.get(participant2_id)
        if not participant2:
            raise ValueError("Participant 2 not found")

    match = Match(
        tournament_id=tournament_id,
        participant1_id=participant1_id,
        participant2_id=participant2_id,
        group_id=group_id,
        playoff_match_id=playoff_match_id,
        type=type,
        format=format,
        status="scheduled",
        is_playoff=playoff_match_id is not None,
        number=number
    )

    db.session.add(match)
    return match


def update_match_results(tournament_id: UUID, match_id: UUID, winner_id: UUID = None, status: str = None):
    """
    Update the results of a match, validating status and winner.
    Handles cases with no participants or one participant.

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.
        winner_id: The UUID of the winner (User or Team), or None.
        status: The new status of the match (e.g., 'completed', 'cancelled').

    Returns:
        Match: The updated match object.

    Raises:
        ValueError: If tournament, match, winner, or status is invalid.
    """
    match = get_match(tournament_id, match_id)
    if match.status == "completed":
        raise ValueError("Match is already completed")

    try:
        # Handle no participants
        if not match.participant1_id and not match.participant2_id:
            if status != "cancelled":
                status = "cancelled"
            match.status = status
            match.winner_id = None
            db.session.add(match)
            db.session.commit()
            return match

        # Handle winner
        if winner_id:
            winner = User.query.get(winner_id) or Team.query.get(winner_id)
            if not winner:
                raise ValueError("Winner not found")
            if winner_id not in [match.participant1_id, match.participant2_id]:
                raise ValueError("Winner must be one of the participants")
            match.winner_id = winner_id

        # Handle status
        if status:
            valid_statuses = ["scheduled", "ongoing",
                              "completed", "cancelled"]
            if status not in valid_statuses:
                raise ValueError(
                    f"Invalid match status. Must be one of {valid_statuses}")
            if status == "completed" and not winner_id:
                raise ValueError("Winner ID is required for completed status")
            match.status = status

        db.session.add(match)
        db.session.commit()
        return match

    except IntegrityError as e:
        db.session.rollback()
        raise ValueError(f"Failed to update match results: {str(e)}")


def register_for_tournament(tournament_id: UUID, participant_id: UUID, is_team: bool = False):
    """
    Register a user or team for a tournament.

    Args:
        tournament_id: The UUID of the tournament.
        participant_id: The UUID of the user or team.
        is_team: Whether the participant is a team (True) or user (False).

    Returns:
        Tournament: The updated tournament object.

    Raises:
        ValueError: If tournament, participant, or registration conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status != "open":
        raise ValueError("Tournament is not open for registration")

    if tournament.max_players and len(tournament.participants) + len(tournament.teams) >= tournament.max_players:
        raise ValueError("Tournament has reached maximum participants")

    if is_team:
        team = Team.query.get(participant_id)
        if not team:
            raise ValueError("Team not found")
        if team in tournament.teams:
            raise ValueError("Team is already registered")
        tournament.teams.append(team)
    else:
        user = User.query.get(participant_id)
        if not user:
            raise ValueError("User not found")
        if user in tournament.participants:
            raise ValueError("User is already registered")
        tournament.participants.append(user)

    # with db.session.begin():
    db.session.add(tournament)
    return tournament


def unregister_for_tournament(tournament_id: UUID, participant_id: UUID, is_team: bool = False):
    """
    Unregister a user or team from a tournament.

    Args:
        tournament_id: The UUID of the tournament.
        participant_id: The UUID of the user or team.
        is_team: Whether the participant is a team (True) or user (False).

    Returns:
        Tournament: The updated tournament object.

    Raises:
        ValueError: If tournament, participant, or unregistration conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status != "open":
        raise ValueError("Tournament is not open for unregistration")

    if is_team:
        team = Team.query.get(participant_id)
        if not team:
            raise ValueError("Team not found")
        if team not in tournament.teams:
            raise ValueError("Team is not registered")
        tournament.teams.remove(team)
    else:
        user = User.query.get(participant_id)
        if not user:
            raise ValueError("User not found")
        if user not in tournament.participants:
            raise ValueError("User is not registered")
        tournament.participants.remove(user)

    # with db.session.begin():
    db.session.add(tournament)
    return tournament


def start_tournament(tournament_id: UUID):
    """
    Start a tournament, setting it to 'ongoing' and assigning participants to groups or playoff stage.
    Validates that matches are correctly set up and handles cases with insufficient participants.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        Tournament: The updated tournament object.

    Raises:
        ValueError: If tournament, participants, or match setup is invalid.
    """
    from main import app
    with app.app_context():
        tournament = get_tournament(tournament_id)
        if tournament.status != "open":
            raise ValueError("Tournament is not in open status")

        total_participants = len(
            tournament.participants) if tournament.type == 'solo' else len(tournament.teams)
        if total_participants < 2:
            tournament.status = 'cancelled'
            db.session.add(tournament)
            try:
                scheduled = ScheduledTournament.query.filter_by(
                    tournament_id=tournament_id).first()
                if scheduled:
                    db.session.delete(scheduled)
            except:
                pass
            db.session.commit()
            raise ValueError("Tournament requires at least 2 participants")

        try:
            scheduled = ScheduledTournament.query.filter_by(
                tournament_id=tournament_id).first()
            if scheduled:
                db.session.delete(scheduled)

            # Set tournament status and start time
            tournament.status = "ongoing"
            tournament.start_time = datetime.now(UTC)
            db.session.add(tournament)

            # Assign participants
            if tournament.group_stage:
                assign_participants_to_groups(tournament_id)
                # Новое: назначение участников матчам
                assign_participants_to_group_matches(tournament_id)
            else:
                assign_participants_to_playoff_stage(tournament_id)
                # Validate match setup
                if tournament.playoff_stage:
                    validate_match_setup(tournament_id)

            db.session.commit()
            return tournament

        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Failed to start tournament: {str(e)}")


def validate_match_setup(tournament_id: UUID):
    """
    Validate playoff matches for cases where 1 or 0 participants.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, or matches are invalid.
    """
    tournament = get_tournament(tournament_id)
    first_round_matches = PlayoffStageMatch.query.filter_by(
        playoff_id=tournament.playoff_stage.id,
        round_number="1",
        bracket="winner"
    ).all()
    for match in first_round_matches:
        if not match.match.participant1_id and not match.match.participant2_id:
            match.match.status = "cancelled"
            db.session.add(match.match)
        elif match.match.participant1_id and not match.match.participant2_id:
            match.match.winner_id = match.match.participant1_id
            match.match.status = "cancelled"
            db.session.add(match.match)
            update_next_match_participants(
                tournament_id, match.match.id, match.match.winner_id)
        elif match.match.participant2_id and not match.match.participant1_id:
            match.match.winner_id = match.match.participant2_id
            match.match.status = "cancelled"
            db.session.add(match.match)
            update_next_match_participants(
                tournament_id, match.match.id, match.match.winner_id)


def complete_group_stage(tournament_id: UUID):
    """
    Complete the group stage and assign participants to playoff stage.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, group stage, or matches are invalid.
    """
    tournament = get_tournament(tournament_id)
    if not tournament.group_stage:
        raise ValueError("Tournament does not have a group stage")

    group_stage = tournament.group_stage
    for group in group_stage.groups:
        for match in group.matches:
            if match.status != "completed" and match.status != 'cancelled':
                raise ValueError("Not all group stage matches are completed")

    # Assign participants to playoff stage
    assign_participants_to_playoff_stage(tournament_id)

    if tournament.playoff_stage:
        validate_match_setup(tournament_id)

    db.session.commit()


def complete_tournament(tournament_id: UUID):
    """
    Complete a tournament, marking it as 'completed' and assigning prizes based on playoff results.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        Tournament: The updated tournament object.

    Raises:
        ValueError: If tournament, matches, or prize table conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status != "ongoing":
        raise ValueError("Tournament is not ongoing")

    if any(match.status not in ["completed", "cancelled"] for match in tournament.matches):
        raise ValueError("Not all matches are completed")

    if not tournament.playoff_stage:
        raise ValueError(
            "Tournament requires a playoff stage to determine winners")

    if not tournament.prize_table:
        raise ValueError("Prize table is not set")

    # Find the final match (highest round number, bracket 'winner')
    final_match = PlayoffStageMatch.query.filter_by(
        playoff_id=tournament.playoff_stage.id,
        bracket="winner"
    ).order_by(PlayoffStageMatch.round_number.desc()).first()

    if not final_match or not final_match.match or not final_match.match.winner_id:
        raise ValueError("Final match is not completed or has no winner")

    # Assign prizes
    prize_fund = float(tournament.prize_fund) if tournament.prize_fund else 0
    winner_id = final_match.match.winner_id
    loser_id = final_match.match.participant1_id if final_match.match.participant2_id == winner_id else final_match.match.participant2_id

    # with db.session.begin():
    # 1st place
    first_place_row = PrizeTableRow.query.filter_by(
        prize_table_id=tournament.prize_table.id, place=1).first()
    first_place_row.user_id = winner_id if User.query.get(winner_id) else None
    first_place_row.team_id = winner_id if Team.query.get(winner_id) else None
    db.session.add(first_place_row)

    second_place_row = PrizeTableRow.query.filter_by(
        prize_table_id=tournament.prize_table.id, place=2).first()
    second_place_row.user_id = loser_id if User.query.get(loser_id) else None
    second_place_row.team_id = loser_id if Team.query.get(loser_id) else None
    db.session.add(second_place_row)

    # 3rd place (optional, based on second-to-last round winner)
    semifinal_matches = PlayoffStageMatch.query.filter_by(
        playoff_id=tournament.playoff_stage.id,
        bracket="winner",
        round_number=str(int(final_match.round_number) - 1)
    ).all()
    semifinal_losers = []
    for match in semifinal_matches:
        if match.match and match.match.winner_id and match.match.participant1_id and match.match.participant2_id:
            loser_id = match.match.participant1_id if match.match.participant2_id == match.match.winner_id else match.match.participant2_id
            semifinal_losers.append(loser_id)
    if semifinal_losers:
        # Pick one semifinal loser for 3rd place (simplified)
        third_place_id = semifinal_losers[0]
        third_place_row = PrizeTableRow.query.filter_by(
            prize_table_id=tournament.prize_table.id, place=3).first()
        third_place_row.user_id = third_place_id if User.query.get(
            third_place_id) else None,
        third_place_row.team_id = third_place_id if Team.query.get(
            third_place_id) else None,
        db.session.add(third_place_row)
    tournament.status = "completed"
    db.session.add(tournament)
    # db.session.commit()

    return tournament


def create_group_row(group_id: UUID, participant_id: UUID, is_team: bool):
    """
    Create a GroupRow entry for a participant in a group, using user_id or team_id based on is_team.

    Args:
        group_id: The UUID of the group.
        participant_id: The UUID of the participant (User or Team).
        is_team: Whether the participant is a team (True) or user (False).

    Returns:
        GroupRow: The created group row object.

    Raises:
        ValueError: If group or participant is not found, or row already exists.
    """
    group = Group.query.get(group_id)
    if not group:
        raise ValueError("Group not found")

    existing_row = GroupRow.query.filter_by(
        group_id=group_id,
        user_id=participant_id if not is_team else None,
        team_id=participant_id if is_team else None
    ).first()
    if existing_row:
        raise ValueError(
            f"GroupRow for participant {participant_id} in group {group_id} already exists")

    participant = Team.query.get(
        participant_id) if is_team else User.query.get(participant_id)
    if not participant:
        raise ValueError(f"Participant {participant_id} not found")

    group_row = GroupRow(
        id=uuid.uuid4(),
        group_id=group_id,
        user_id=participant_id if not is_team else None,
        team_id=participant_id if is_team else None,
        place=0,
        wins=0,
        draws=0,
        loses=0
    )

    db.session.add(group_row)
    return group_row


def make_group_stage(tournament_id: UUID, num_groups: int, max_participants_per_group: int, participants: list, winners_bracket_qualified: int):
    """
    Create a group stage for a tournament with specified groups, distributing placeholder participants.

    Args:
        tournament_id: The UUID of the tournament.
        num_groups: Number of groups to create.
        max_participants_per_group: Maximum participants per group.
        participants: List of participant placeholders (None for TBD).
        winners_bracket_qualified: Number of participants advancing to playoff.

    Returns:
        GroupStage: The created group stage object.

    Raises:
        ValueError: If tournament, group parameters, or participant conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status != "open":
        raise ValueError(
            "Tournament must be in open status to create group stage")

    if tournament.group_stage:
        raise ValueError("Group stage already exists")

    if len(participants) < num_groups * 2:
        raise ValueError("Not enough participants for the number of groups")

    if num_groups < 1 or max_participants_per_group < 2:
        raise ValueError("Invalid number of groups or participants per group")

    group_stage = GroupStage(
        tournament_id=tournament_id,
        winners_bracket_qualified=winners_bracket_qualified
    )

    db.session.add(group_stage)
    db.session.flush()  # Get group_stage.id

    participants_per_group = len(participants) // num_groups
    remainder = len(participants) % num_groups
    if participants_per_group > max_participants_per_group:
        raise ValueError("Too many participants for the specified group size")

    for i in range(num_groups):
        group_letter = chr(65 + i)  # A, B, C, ...
        start = i * participants_per_group
        end = start + participants_per_group + (1 if i < remainder else 0)
        group_participants = participants[start:end]
        group_stage.groups.append(make_group(
            groupstage_id=group_stage.id,
            letter=group_letter,
            max_participants=max_participants_per_group,
            participants=group_participants,
            is_team=tournament.type == "team"
        ))

    return group_stage


def make_group(groupstage_id: UUID, letter: str, max_participants: int, participants: list, is_team: bool):
    """
    Create a group within a group stage and create GroupRow entries for placeholders.

    Args:
        groupstage_id: The UUID of the group stage.
        letter: The group letter (e.g., 'A', 'B').
        max_participants: Maximum participants in the group.
        participants: List of participant placeholders (None for TBD).
        is_team: Whether the participants are teams (True) or users (False).

    Returns:
        Group: The created group object.

    Raises:
        ValueError: If group stage, letter, participants, or conditions are invalid.
    """
    group_stage = GroupStage.query.get(groupstage_id)
    if not group_stage:
        raise ValueError("Group stage not found")

    if Group.query.filter_by(groupstage_id=groupstage_id, letter=letter).first():
        raise ValueError(f"Group {letter} already exists in this group stage")

    if max_participants < 2:
        raise ValueError("Group must allow at least 2 participants")

    group = Group(
        groupstage_id=groupstage_id,
        letter=letter,
        max_participants=max_participants
    )

    db.session.add(group)
    db.session.flush()  # Ensure group.id is available

    for participant in participants:
        group_row = GroupRow(
            id=uuid.uuid4(),
            group_id=group.id,
            user_id=None if not is_team else None,
            team_id=None if is_team else None,
            place=0,
            wins=0,
            draws=0,
            loses=0
        )
        db.session.add(group_row)

    return group


def generate_single_elimination_bracket(tournament_id: UUID, participants: list[UUID], match_start_idx: int = 1):
    """
    Generate a single-elimination playoff bracket for a tournament with placeholder participants.

    Args:
        tournament_id: The UUID of the tournament.
        participants: List of placeholder participant UUIDs (None for TBD).

    Returns:
        PlayoffStage: The created playoff stage object.

    Raises:
        ValueError: If tournament, participants, or conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status != "open":
        raise ValueError(
            "Tournament must be in open status to create playoff stage")

    if tournament.playoff_stage:
        raise ValueError("Playoff stage already exists")

    if len(participants) < 2:
        raise ValueError(
            "At least 2 participants are required for playoff stage")

    total_participants = len(participants)
    num_slots = 2 ** math.ceil(math.log2(total_participants))
    rounds = int(math.log2(num_slots))

    playoff_stage = PlayoffStage(tournament_id=tournament_id)

    db.session.add(playoff_stage)
    db.session.flush()

    matches = []
    for i in range(num_slots // 2):
        match = Match(
            tournament_id=tournament_id,
            participant1_id=None,
            participant2_id=None,
            type="playoff",
            format='bo1' if tournament.match_format == 'bo2' else tournament.match_format,
            status="scheduled",
            number=match_start_idx
        )
        match_start_idx += 1
        db.session.add(match)
        db.session.flush()
        playoff_match = PlayoffStageMatch(
            playoff_id=playoff_stage.id,
            match=match,
            round_number=str(1),
            bracket="winner"
        )
        db.session.add(playoff_match)
        matches.append(playoff_match)

    for round_num in range(2, rounds + 1):
        num_matches_in_round = num_slots // (2 ** round_num)
        for i in range(num_matches_in_round):
            match = Match(
                tournament_id=tournament_id,
                type="playoff",
                format='bo1' if tournament.match_format == 'bo2' else tournament.match_format if round_num < rounds else tournament.final_format,
                status="scheduled",
                number=match_start_idx
            )
            match_start_idx += 1
            db.session.add(match)
            db.session.flush()
            playoff_match = PlayoffStageMatch(
                playoff_id=playoff_stage.id,
                match=match,
                round_number=str(round_num),
                bracket="winner"
            )
            db.session.add(playoff_match)
            matches.append(playoff_match)

    for round_num in range(1, rounds):
        matches_in_round = [m for m in matches if int(
            m.round_number) == round_num]
        next_round_matches = [
            m for m in matches if int(m.round_number) == round_num + 1]
        for i, match in enumerate(matches_in_round):
            next_match = next_round_matches[i // 2]
            if i % 2 == 0:
                next_match.depends_on_match_1_id = match.id
            else:
                next_match.depends_on_match_2_id = match.id

    return playoff_stage


def complete_map(tournament_id: UUID, match_id: UUID, map_id: UUID, winner_id: UUID | None):
    """
    Complete a map by setting its winner, updating match scores, and completing the match if needed.
    Handles cases with one participant and draws (winner_id=None).

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.
        map_id: The UUID of the map.
        winner_id: The UUID of the winner (User or Team), or None for a draw.

    Returns:
        Map: The updated map object.

    Raises:
        ValueError: If tournament, match, map, or winner is invalid.
    """
    match = get_match(tournament_id, match_id)
    if match.status not in ["ongoing", "scheduled"]:
        raise ValueError("Match must be in 'ongoing' or 'scheduled' status")

    map_ = Map.query.get(map_id)
    if not map_ or map_.match_id != match_id:
        raise ValueError("Map not found or does not belong to the match")

    if map_.winner_id is not None:
        raise ValueError("Map already completed")

    # Handle case with one participant
    if (match.participant1_id and not match.participant2_id) or (match.participant2_id and not match.participant1_id):
        winner_id = match.participant1_id or match.participant2_id
    elif winner_id is not None:  # Validate winner_id only if it's not None
        winner = User.query.get(winner_id) or Team.query.get(winner_id)
        if not winner:
            raise ValueError("Winner not found")
        if winner_id not in [match.participant1_id, match.participant2_id]:
            raise ValueError("Winner must be one of the match participants")

    try:
        # Update map
        map_.winner_id = winner_id

        # Update match scores (do not increment scores for a draw)
        if winner_id == match.participant1_id:
            match.participant1_score += 1
        elif winner_id == match.participant2_id:
            match.participant2_score += 1

        db.session.add(map_)
        db.session.add(match)

        # Check if all maps are completed and handle match completion
        if all(m.winner_id is not None for m in match.maps):
            if match.format.startswith("bo"):
                num_maps = int(match.format[2:])
                # Handle BO2 draw case
                if match.format == "bo2" and match.participant1_score == 1 and match.participant2_score == 1:
                    complete_match(tournament_id, match_id, None)  # Draw
                elif match.participant1_score > num_maps // 2:
                    complete_match(tournament_id, match_id,
                                   match.participant1_id)
                elif match.participant2_score > num_maps // 2:
                    complete_match(tournament_id, match_id,
                                   match.participant2_id)
                elif match.participant1_id and not match.participant2_id:
                    complete_match(tournament_id, match_id,
                                   match.participant1_id)
                elif match.participant2_id and not match.participant1_id:
                    complete_match(tournament_id, match_id,
                                   match.participant2_id)

        db.session.commit()
        return map_

    except IntegrityError as e:
        db.session.rollback()
        raise ValueError("Failed to update map or match due to database error")


def sort_group_standings(group_id: UUID):
    """
    Sort participants in a group by recalculating points (2 for win, 1 for draw, 0 for loss)
    and updating their place in GroupRow.

    Args:
        group_id: The UUID of the group.

    Raises:
        ValueError: If group is not found or GroupRow data is invalid.
    """
    group = Group.query.get(group_id)
    if not group:
        raise ValueError("Group not found")

    try:
        # Get all GroupRow entries for the group
        group_rows = GroupRow.query.filter_by(group_id=group_id).all()
        if not group_rows:
            raise ValueError(f"No participants found in group {group_id}")

        # Calculate points and sort (2 points for win, 1 for draw, 0 for loss)
        standings = [
            {
                "row": row,
                "points": (row.wins * 2) + (row.draws * 1),
                "wins": row.wins
            }
            for row in group_rows
        ]
        standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)

        # Assign places (1-based indexing)
        for index, standing in enumerate(standings, 1):
            row = standing["row"]
            row.place = index
            db.session.add(row)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to sort group standings: {str(e)}")


def complete_match(tournament_id: UUID, match_id: UUID, winner_id: UUID = None):
    """
    Complete a match by setting its winner and updating next matches.
    For group stage matches, update GroupRow statistics (wins, loses, draws) and sort standings.
    For bo2 group stage matches, handle draws if no winner is specified.
    If the match is the final match, complete the tournament.
    Group stage matches must have both participants.

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.
        winner_id: The UUID of the winner (User or Team), or None for a draw in bo2.

    Returns:
        Match: The updated match object.

    Raises:
        ValueError: If tournament, match, winner, or participants are invalid.
    """
    match = get_match(tournament_id, match_id)

    if match.status == "completed":
        raise ValueError("Match is already completed")

    # Handle case with no participants (only for playoff matches)
    if not match.participant1_id and not match.participant2_id:
        if match.group_id:
            raise ValueError("Group stage matches must have both participants")
        match.status = "cancelled"
        db.session.add(match)
        db.session.commit()
        return match

    # Handle case with one participant (only for playoff matches)
    if (match.participant1_id and not match.participant2_id) or (match.participant2_id and not match.participant1_id):
        if match.group_id:
            raise ValueError("Group stage matches must have both participants")
        winner_id = match.participant1_id or match.participant2_id
        match.winner_id = winner_id
        match.status = "cancelled"
    else:
        # Normal case with two participants
        if match.format == "bo2" and winner_id is None:
            # Handle draw for bo2 group stage matches
            match.status = "completed"
            match.winner_id = None
        else:
            if not winner_id:
                raise ValueError(
                    "Winner ID must be provided for matches with two participants, except for bo2 draws")
            match = update_match_results(
                tournament_id, match_id, winner_id, "completed")

    # Update GroupRow for group stage matches
    if match.group_id:
        try:
            # Ensure both participants exist
            if not match.participant1_id or not match.participant2_id:
                raise ValueError(
                    "Group stage matches must have both participants")

            # Find GroupRow entries for both participants
            group_row1 = GroupRow.query.filter_by(
                group_id=match.group_id,
                user_id=match.participant1_id if match.tournament.type == "solo" else None,
                team_id=match.participant1_id if match.tournament.type == "team" else None
            ).first()
            group_row2 = GroupRow.query.filter_by(
                group_id=match.group_id,
                user_id=match.participant2_id if match.tournament.type == "solo" else None,
                team_id=match.participant2_id if match.tournament.type == "team" else None
            ).first()

            # Validate GroupRow existence
            if not group_row1:
                raise ValueError(
                    f"GroupRow not found for participant {match.participant1_id} in group {match.group_id}")
            if not group_row2:
                raise ValueError(
                    f"GroupRow not found for participant {match.participant2_id} in group {match.group_id}")

            # Update statistics based on match result
            if match.format == "bo2" and winner_id is None and match.status == "completed":
                # Handle draw for bo2
                group_row1.draws += 1
                group_row2.draws += 1
                db.session.add(group_row1)
                db.session.add(group_row2)
            elif match.status == "completed" and winner_id:
                # Handle win/loss
                if winner_id == match.participant1_id:
                    group_row1.wins += 1
                    group_row2.loses += 1
                elif winner_id == match.participant2_id:
                    group_row1.loses += 1
                    group_row2.wins += 1
                db.session.add(group_row1)
                db.session.add(group_row2)
            # Sort group standings
            sort_group_standings(match.group_id)

        except Exception as e:
            db.session.rollback()
            raise ValueError(
                f"Failed to update GroupRow statistics or sort standings: {str(e)}")
    matches = Match.query.filter_by(group_id=match.group_id)

    if all(m.status == 'completed' or m.status == 'cancelled' for m in matches):
        complete_group_stage(tournament_id)

    # Update next match participants for playoff matches
    if match.playoff_match and winner_id:
        update_next_match_participants(tournament_id, match_id, winner_id)

    # Check if this is the final match
    if match.playoff_match:
        final_match = PlayoffStageMatch.query.filter_by(
            playoff_id=match.playoff_match.playoff_id,
            bracket="winner"
        ).order_by(PlayoffStageMatch.round_number.desc()).first()
        if final_match and final_match.id == match.playoff_match.id:
            tournament = get_tournament(tournament_id)
            if all(m.status in ["completed", "cancelled"] for m in tournament.matches):
                complete_tournament(tournament_id)

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise ValueError("Failed to complete match due to database error")

    return match


def update_next_match_participants(tournament_id: UUID, match_id: UUID, winner_id: UUID):
    """
    Update the participants of the next match based on the current match's winner.
    Handles cases with one or no participants in the next match.

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.
        winner_id: The UUID of the winner (User or Team).

    Returns:
        None

    Raises:
        ValueError: If tournament, match, or next match is invalid.
    """
    match = get_match(tournament_id, match_id)
    if not match.playoff_match:
        return

    playoff_match = match.playoff_match
    next_winner_match = PlayoffStageMatch.query.filter_by(
        playoff_id=playoff_match.playoff_id,
        depends_on_match_1_id=playoff_match.id
    ).first() or PlayoffStageMatch.query.filter_by(
        playoff_id=playoff_match.playoff_id,
        depends_on_match_2_id=playoff_match.id
    ).first()

    if not next_winner_match:
        return

    try:
        if next_winner_match.match:
            next_match = next_winner_match.match
            if not next_match.participant1_id:
                next_match.participant1_id = winner_id
            elif not next_match.participant2_id:
                next_match.participant2_id = winner_id
            else:
                raise ValueError(
                    "Next winner match already has both participants")

            db.session.add(next_match)

            # Check if next match can be auto-completed
            parallel_match = next_winner_match.depends_on_match_1 if next_winner_match.depends_on_match_2_id == playoff_match.id else next_winner_match.depends_on_match_2
            if parallel_match and parallel_match.match.status == "cancelled":
                if next_match.participant1_id and not next_match.participant2_id:
                    next_match.winner_id = next_match.participant1_id
                    next_match.status = "cancelled"
                    db.session.add(next_match)
                    update_next_match_participants(
                        tournament_id, next_match.id, next_match.winner_id)
                elif next_match.participant2_id and not next_match.participant1_id:
                    next_match.winner_id = next_match.participant2_id
                    next_match.status = "cancelled"
                    db.session.add(next_match)
                    update_next_match_participants(
                        tournament_id, next_match.id, next_match.winner_id)

        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        raise ValueError(
            "Failed to update next match participants due to database constraints")


def create_prizetable(tournament_id: UUID):
    """
    Create a prize table for a tournament.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        PrizeTable: The created prize table object.

    Raises:
        ValueError: If tournament or conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    if tournament.prize_table:
        raise ValueError("Prize table already exists")

    if tournament.status == "completed":
        raise ValueError("Cannot create prize table for completed tournament")

    prize_table = PrizeTable(tournament_id=tournament_id)
    db.session.add(prize_table)
    return prize_table


def create_prizetable_row(tournament_id: UUID, place: int, user_id: UUID = None, team_id: UUID = None, prize: float = 0.0):
    """
    Create a row in a tournament's prize table.

    Args:
        tournament_id: The UUID of the tournament.
        place: The place (e.g., 1 for 1st place).
        user_id: The UUID of the user (optional).
        team_id: The UUID of the team (optional).
        prize: The prize amount.

    Returns:
        PrizeTableRow: The created prize table row object.

    Raises:
        ValueError: If tournament, prize table, or conditions are invalid.
    """
    tournament = get_tournament(tournament_id)

    prize_table = tournament.prize_table
    if not prize_table:
        raise ValueError("Prize table does not exist")

    if PrizeTableRow.query.filter_by(prize_table_id=prize_table.id, place=place).first():
        raise ValueError(f"Prize table row for place {place} already exists")

    if user_id and team_id:
        raise ValueError("Cannot assign both user and team to prize table row")

    if user_id:
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        if user not in tournament.participants:
            raise ValueError("User is not a participant in the tournament")
    if team_id:
        team = Team.query.get(team_id)
        if not team:
            raise ValueError("Team not found")
        if team not in tournament.teams:
            raise ValueError("Team is not a participant in the tournament")

    if prize < 0 or (tournament.prize_fund and float(tournament.prize_fund) > 0 and prize > float(tournament.prize_fund)):
        raise ValueError("Invalid prize amount")

    row = PrizeTableRow(
        prize_table_id=prize_table.id,
        place=place,
        user_id=user_id,
        team_id=team_id,
        prize=str(prize)
    )

    db.session.add(row)
    return row


def assign_participants_to_groups(tournament_id: UUID):
    """
    Assign participants to groups in the group stage of a tournament, distributing them evenly.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, group stage, or groups are not found, or insufficient participants.
    """
    tournament = get_tournament(tournament_id)

    if not tournament.group_stage:
        raise ValueError("Tournament does not have a group stage")

    group_stage = tournament.group_stage
    if not group_stage:
        raise ValueError("Group stage not found")

    groups = group_stage.groups
    if not groups:
        raise ValueError("No groups found in group stage")

    # Collect participants (users or teams based on tournament type)
    participants = tournament.teams if tournament.type == "team" else tournament.participants
    if len(participants) < 2:
        raise ValueError("Tournament requires at least 2 participants")

    # Calculate total max participants across all groups
    total_max_participants = sum(group.max_participants for group in groups)
    if len(participants) > total_max_participants:
        raise ValueError("Too many participants for available group slots")

    # Shuffle participants for random assignment
    participants = list(participants)
    random.shuffle(participants)

    try:
        # Clear existing GroupRow entries for all groups
        for group in groups:
            GroupRow.query.filter_by(group_id=group.id).delete()
            # Clear group participants/teams to avoid duplicates
            if tournament.type == 'solo':
                group.participants.clear()
            else:
                group.teams.clear()

        # Calculate target number of participants per group
        num_groups = len(groups)
        base_participants_per_group = len(participants) // num_groups
        extra_participants = len(participants) % num_groups

        # Distribute participants evenly using round-robin
        participant_index = 0
        for i in range(len(participants)):
            # Assign to group i % num_groups
            group_index = i % num_groups
            group = groups[group_index]

            # Check if group can accept more participants
            current_participants = len(
                group.participants) if tournament.type == 'solo' else len(group.teams)
            if current_participants >= group.max_participants:
                continue

            if participant_index >= len(participants):
                break

            participant = participants[participant_index]

            # Add participant to group
            if tournament.type == 'solo':
                group.participants.append(participant)
            else:
                group.teams.append(participant)

            # Create GroupRow entry
            create_group_row(
                group_id=group.id,
                participant_id=participant.id,
                is_team=tournament.type == "team"
            )
            participant_index += 1

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to assign participants to groups: {str(e)}")


def assign_participants_to_playoff_stage(tournament_id: UUID):
    """
    Assign participants to the playoff stage, distributing each to a separate match in the first round.
    Handles cases with one or no participants per match.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, playoff stage, or insufficient participants.
    """
    tournament = get_tournament(tournament_id)
    playoff_stage = tournament.playoff_stage
    if not playoff_stage:
        raise ValueError("Playoff stage not found")

    participants = []
    if tournament.group_stage:
        group_stage = tournament.group_stage
        if not group_stage:
            raise ValueError("Group stage not found")
        for group in group_stage.groups:
            group_rows = GroupRow.query.filter_by(group_id=group.id).order_by(
                GroupRow.place.asc(), GroupRow.wins.desc()
            ).limit(group_stage.winners_bracket_qualified).all()
            participants.extend(
                row.team if tournament.type == "team" else row.user
                for row in group_rows
            )
    else:
        participants = tournament.teams if tournament.type == "team" else tournament.participants

    # print("Participants: ", participants)

    if len(participants) < 2:
        raise ValueError("Insufficient participants for playoff stage")

    # Validate playoff structure
    num_slots = 2 ** math.ceil(math.log2(len(participants)))
    if len(participants) > num_slots:
        raise ValueError("Too many participants for playoff structure")

    try:
        # Shuffle participants for random seeding
        participants = list(participants)
        random.shuffle(participants)

        # Get first round matches
        first_round_matches = PlayoffStageMatch.query.filter_by(
            playoff_id=playoff_stage.id,
            round_number="1",
            bracket="winner"
        ).order_by(PlayoffStageMatch.id).all()
        # print("FRM", first_round_matches)

        # Distribute participants
        participant_index = 0
        for match in first_round_matches:
            match.match.participant1_id = participants[participant_index].id if participant_index < len(
                participants) else None
            # print(match.match.participant1_id)
            participant_index += 1
            match.match.participant2_id = participants[participant_index].id if participant_index < len(
                participants) else None
            participant_index += 1

            db.session.add(match.match)

            # Handle matches with one or no participants
            if not match.match.participant1_id and not match.match.participant2_id:
                match.match.status = "cancelled"
                db.session.add(match.match)
            elif match.match.participant1_id and not match.match.participant2_id:
                match.match.winner_id = match.match.participant1_id
                match.match.status = "cancelled"
                db.session.add(match.match)
                update_next_match_participants(
                    tournament_id, match.match.id, match.match.winner_id)
            elif match.match.participant2_id and not match.match.participant1_id:
                match.match.winner_id = match.match.participant2_id
                match.match.status = "cancelled"
                db.session.add(match.match)
                update_next_match_participants(
                    tournament_id, match.match.id, match.match.winner_id)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to assign participants: {str(e)}")


def assign_users_to_prizetable(tournament_id: UUID):
    """
    Assign participants to the prize table based on playoff results.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, playoff stage, or final match is invalid.
    """
    tournament = get_tournament(tournament_id)
    if not tournament.playoff_stage:
        raise ValueError("Tournament requires a playoff stage")

    if not tournament.prize_table:
        raise ValueError("Prize table not set")

    # Find the final match (highest round number, bracket 'winner')
    final_match = PlayoffStageMatch.query.filter_by(
        playoff_id=tournament.playoff_stage.id,
        bracket="winner"
    ).order_by(PlayoffStageMatch.round_number.desc()).first()

    if not final_match or not final_match.match or not final_match.match.winner_id:
        raise ValueError("Final match is not completed or has no winner")

    prize_fund = float(tournament.prize_fund) if tournament.prize_fund else 0
    winner_id = final_match.match.winner_id
    loser_id = final_match.match.participant1_id if final_match.match.participant2_id == winner_id else final_match.match.participant2_id

    # Clear existing prize table rows to avoid duplicates
    PrizeTableRow.query.filter_by(
        prize_table_id=tournament.prize_table.id).delete()

    # 1st place
    create_prizetable_row(
        tournament_id=tournament.id,
        place=1,
        user_id=winner_id if User.query.get(winner_id) else None,
        team_id=winner_id if Team.query.get(winner_id) else None,
        prize=prize_fund * 0.5
    )

    # 2nd place
    create_prizetable_row(
        tournament_id=tournament.id,
        place=2,
        user_id=loser_id if User.query.get(loser_id) else None,
        team_id=loser_id if Team.query.get(loser_id) else None,
        prize=prize_fund * 0.3
    )

    # 3rd place (from semifinal losers)
    semifinal_matches = PlayoffStageMatch.query.filter_by(
        playoff_id=tournament.playoff_stage.id,
        bracket="winner",
        round_number=str(int(final_match.round_number) - 1)
    ).all()
    semifinal_losers = []
    for match in semifinal_matches:
        if match.match and match.match.winner_id and match.match.participant1_id and match.match.participant2_id:
            loser_id = match.match.participant1_id if match.match.participant2_id == match.match.winner_id else match.match.participant2_id
            semifinal_losers.append(loser_id)

    if semifinal_losers:
        third_place_id = semifinal_losers[0]  # Simplified: take first loser
        create_prizetable_row(
            tournament_id=tournament.id,
            place=3,
            user_id=third_place_id if User.query.get(third_place_id) else None,
            team_id=third_place_id if Team.query.get(third_place_id) else None,
            prize=prize_fund * 0.2
        )

    db.session.commit()


def reset_tournament(tournament_id: UUID):
    """
    Reset a tournament by deleting all related stages, matches, and prize table,
    and setting status back to 'open'. Participants and teams are preserved.

    Args:
        tournament_id: The UUID of the tournament.

    Returns:
        Tournament: The reset tournament object.

    Raises:
        ValueError: If tournament is not found or already in 'open' status.
    """
    tournament = get_tournament(tournament_id)

    if tournament.status == "open":
        raise ValueError("Tournament is already in open status")

    try:
        # Delete GroupStage (Groups and GroupRows are deleted via CASCADE)
        GroupStage.query.filter_by(tournament_id=tournament_id).delete()

        # Delete PlayoffStage (PlayoffStageMatches and Matches are deleted via CASCADE)
        PlayoffStage.query.filter_by(tournament_id=tournament_id).delete()

        # Delete Matches (Maps are deleted via CASCADE)
        Match.query.filter_by(tournament_id=tournament_id).delete()

        # Delete PrizeTable (PrizeTableRows are deleted via CASCADE)
        PrizeTable.query.filter_by(tournament_id=tournament_id).delete()

        # Reset tournament status and clear relationships
        tournament.status = "open"
        tournament.start_time = "2025-06-01 15:00:00"
        tournament.group_stage = None
        tournament.playoff_stage = None
        tournament.prize_table = None
        tournament.matches = []

        db.session.add(tournament)
        db.session.commit()

        # Remove scheduled task
        try:
            from apscheduler_tasks import scheduler
            from apscheduler.jobstores.base import JobLookupError
            scheduler.remove_job(f"tournament_start_{tournament_id}")
        except JobLookupError:
            pass

        return tournament

    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to reset tournament: {str(e)}")


def start_match(tournament_id: UUID, match_id: UUID):
    """
    Start a match by setting its status to 'ongoing' and creating maps based on the match format.

    Args:
        tournament_id: The UUID of the tournament.
        match_id: The UUID of the match.

    Returns:
        Match: The updated match object with status 'ongoing' and created maps.

    Raises:
        ValueError: If tournament, match, or participants are invalid, or match is not in 'scheduled' status.
    """
    # Get match and validate
    match = get_match(tournament_id, match_id)

    if match.status != "scheduled":
        raise ValueError("Match must be in 'scheduled' status to start")

    if not match.participant1_id or not match.participant2_id:
        raise ValueError("Match cannot start without both participants")

    # Set match status to ongoing
    match.status = "ongoing"

    # Initialize scores if not set
    match.participant1_score = match.participant1_score or 0
    match.participant2_score = match.participant2_score or 0

    # Create maps based on format
    if not match.format.startswith("bo"):
        raise ValueError("Invalid match format. Expected 'boX' (e.g., 'bo3')")

    try:
        num_maps = int(match.format[2:])  # e.g., 'bo3' -> 3
    except ValueError:
        raise ValueError(
            "Invalid match format. Expected 'boX' where X is a number")

    # Check if maps already exist
    if match.maps:
        raise ValueError("Maps already created for this match")

    # Create maps
    for i in range(num_maps):
        map_ = Map(
            match_id=match_id,
            # Optional: external_id=str(uuid.uuid4()),  # If external_id is needed
            # Optional: order=i+1  # If Map model has order
        )
        db.session.add(map_)

    try:
        db.session.add(match)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise ValueError("Failed to start match due to database error")

    return match


def create_group_stage_matches(tournament_id: UUID, participants, format_: str):
    """
    Create matches for the group stage of a tournament, generating round-robin matches for each group
    with no participants assigned.

    Args:
        tournament_id: The UUID of the tournament.
        participants: Ignored (kept for compatibility).
        format_: The match format (e.g., 'bo1', 'bo3').

    Returns:
        list: List of created Match objects.

    Raises:
        ValueError: If tournament, group stage, or groups are invalid.
    """
    tournament = get_tournament(tournament_id)

    if not tournament.group_stage:
        raise ValueError("Tournament does not have a group stage")

    group_stage = tournament.group_stage
    if not group_stage:
        raise ValueError("Group stage not found")

    groups = group_stage.groups
    if not groups:
        raise ValueError("No groups found in group stage")

    created_matches = []
    match_number = 1

    try:
        for group in groups:
            # Количество матчей для round-robin: C(n,2) = n*(n-1)/2, где n = max_participants
            max_participants = group.max_participants
            num_matches = (max_participants * (max_participants - 1)) // 2
            if num_matches < 1:
                continue

            for _ in range(num_matches):
                match = create_match(
                    tournament_id=tournament_id,
                    participant1_id=None,  # Без участников
                    participant2_id=None,  # Без участников
                    group_id=group.id,
                    type="group",
                    format=format_,
                    number=match_number
                )
                match_number += 1
                created_matches.append(match)

        db.session.commit()
        return created_matches

    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Failed to create group stage matches: {str(e)}")


def assign_participants_to_group_matches(tournament_id: UUID):
    """
    Assign participants to group stage matches in a round-robin format.

    Args:
        tournament_id: The UUID of the tournament.

    Raises:
        ValueError: If tournament, group stage, groups, or matches are invalid.
    """
    tournament = get_tournament(tournament_id)

    if not tournament.group_stage:
        raise ValueError("Tournament does not have a group stage")

    group_stage = tournament.group_stage
    if not group_stage:
        raise ValueError("Group stage not found")

    groups = group_stage.groups
    if not groups:
        raise ValueError("No groups found in group stage")

    try:
        for group in groups:
            # Получаем участников группы
            participants = group.teams if tournament.type == "team" else group.participants
            if len(participants) < 2:
                continue

            # Перемешиваем участников для случайного распределения
            participants = list(participants)
            random.shuffle(participants)

            # Получаем все матчи группы
            matches = Match.query.filter_by(group_id=group.id).all()
            if not matches:
                raise ValueError(f"No matches found for group {group.letter}")

            # Рассчитываем необходимое количество матчей
            expected_matches = (len(participants) *
                                (len(participants) - 1)) // 2
            if len(matches) < expected_matches:
                raise ValueError(
                    f"Insufficient matches for group {group.letter}")
            for m in matches[expected_matches:]:
                m.status = 'cancelled' #TODO Fix

            # Назначаем участников матчам в формате round-robin
            match_index = 0
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    if match_index >= len(matches):
                        break
                    match = matches[match_index]
                    match.participant1_id = participants[i].id
                    match.participant2_id = participants[j].id
                    # print(match.participant1_id, match.participant2_id)
                    if not match.participant2_id and not match.participant1_id:
                        match.status = 'cancelled'
                    db.session.add(match)
                    match_index += 1

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise ValueError(
            f"Failed to assign participants to group matches: {str(e)}")
