from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models import Team, User, UserRequest
from flask_jwt_extended import get_jwt_identity
from datetime import datetime, UTC


def get_current_user() -> User:
    """Get the current user from JWT identity."""
    user_id = get_jwt_identity()
    if not user_id:
        raise ValueError("Invalid JWT token")

    try:
        user = User.query.get(UUID(user_id))
    except ValueError:
        raise ValueError("Invalid user ID format")

    if not user:
        raise ValueError("User not found")

    return user


def create_team(title: str, description: str = None, logo_path: str = None) -> Team:
    """Create a new team with the current user as leader and member."""
    current_user = get_current_user()

    if not title or not title.strip():
        raise ValueError("Team title is required")

    if Team.query.filter_by(title=title).first():
        raise ValueError("Team with this title already exists")

    team = Team(
        title=title.strip(),
        description=description.strip() if description else None,
        logo_path=logo_path.strip() if logo_path else None,
        leader_id=current_user.id
    )
    team.players.append(current_user)
    db.session.add(team)
    return team


def update_team(team_id: UUID, title: str = None, description: str = None, logo_path: str = None) -> Team:
    """Update team information."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")

    current_user = get_current_user()
    if team.leader_id != current_user.id:
        raise PermissionError(
            "Only the team leader can update team information")

    if title and not title.strip():
        raise ValueError("Team title cannot be empty")

    if title and title != team.title and Team.query.filter(Team.title == title, Team.id != team_id).first():
        raise ValueError("Team with this title already exists")

    if title:
        team.title = title.strip()
    if description is not None:
        team.description = description.strip() if description else None
    if logo_path is not None:
        team.logo_path = logo_path.strip() if logo_path else None

    return team


def delete_team(team_id: UUID) -> None:
    """Delete a team."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")

    current_user = get_current_user()
    if team.leader_id != current_user.id:
        raise PermissionError("Only the team leader can delete the team")

    db.session.delete(team)


def get_team(team_id: UUID) -> Team:
    """Get a team by ID."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")
    return team


def get_teams(page: int = 1, per_page: int = 10) -> list:
    """Get a paginated list of all teams."""
    return Team.query.options(joinedload(Team.players)).paginate(page=page, per_page=per_page, error_out=False).items


def get_team_members(team_id: UUID) -> list:
    """Get the list of team members."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")
    return team.players


def invite_user_to_team(to_user_id: UUID, team_id: UUID) -> UserRequest:
    """Create an invitation to join a team."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")

    to_user = User.query.get(to_user_id)
    if not to_user:
        raise ValueError("User not found")

    current_user = get_current_user()
    if current_user not in team.players:
        raise PermissionError("Only team members can send invitations")

    if to_user in team.players:
        raise ValueError("User is already a team member")

    existing = UserRequest.query.filter_by(
        from_user_id=current_user.id,
        to_user_id=to_user_id,
        type='team',
        team_id=team_id,
        status='pending'
    ).first()
    if existing:
        raise ValueError("Invitation already sent")

    request = UserRequest(
        from_user_id=current_user.id,
        to_user_id=to_user_id,
        type='team',
        team_id=team_id,
        status='pending',
        created_at=datetime.now(UTC)
    )
    db.session.add(request)
    return request


def accept_team_invite(request_id: UUID) -> Team:
    """Accept a team invitation."""
    request = UserRequest.query.get(request_id)
    if not request or request.type != 'team' or request.status != 'pending':
        raise ValueError("Invalid or non-pending team invitation")

    current_user = get_current_user()
    if request.to_user_id != current_user.id:
        raise ValueError("Only the invited user can accept the invitation")

    team = Team.query.get(request.team_id)
    if not team:
        raise ValueError("Team not found")

    if current_user in team.players:
        raise ValueError("User is already a team member")

    team.players.append(current_user)
    request.status = 'accepted'
    request.updated_at = datetime.now(UTC)
    return team


def decline_team_invite(request_id: UUID) -> None:
    """Decline a team invitation."""
    request = UserRequest.query.get(request_id)
    if not request or request.type != 'team' or request.status != 'pending':
        raise ValueError("Invalid or non-pending team invitation")

    current_user = get_current_user()
    if request.to_user_id != current_user.id:
        raise ValueError("Only the invited user can decline the invitation")

    request.status = 'declined'
    request.updated_at = datetime.now(UTC)


def leave_team(team_id: UUID) -> None:
    """Leave a team."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")

    current_user = get_current_user()
    if current_user not in team.players:
        raise ValueError("User is not a team member")

    if team.leader_id == current_user.id:
        raise PermissionError(
            "Team leader cannot leave the team; delete the team instead")

    team.players.remove(current_user)


def kick_member(team_id: UUID, user_to_kick_id: UUID) -> None:
    """Kick a member from a team."""
    team = Team.query.get(team_id)
    if not team:
        raise ValueError("Team not found")

    current_user = get_current_user()
    if team.leader_id != current_user.id:
        raise PermissionError("Only the team leader can kick members")

    if team.leader_id == user_to_kick_id:
        raise ValueError("Leader cannot kick themselves")

    user_to_kick = User.query.get(user_to_kick_id)
    if not user_to_kick:
        raise ValueError("User not found")

    if user_to_kick not in team.players:
        raise ValueError("User is not a team member")

    team.players.remove(user_to_kick)


def get_user_team_invites() -> list:
    """Get all pending team invitations for the current user."""
    current_user = get_current_user()
    return UserRequest.query.filter(
        ((UserRequest.from_user_id == current_user.id)
         | (UserRequest.to_user_id == current_user.id)),
        UserRequest.type == 'team',
        UserRequest.status == 'pending'
    ).options(
        joinedload(UserRequest.team),
        joinedload(UserRequest.from_user),
        joinedload(UserRequest.to_user)
    ).all()
