from flask import abort
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from app.extensions import db
from app.models import Game, Achievement, User


def get_all_games():
    """Retrieve all games from the database."""
    return Game.query.all()


def get_game(game_id: UUID):
    """Retrieve a game by its ID."""
    return Game.query.get_or_404(game_id)


def create_game(title: str, image_path: str = None, logo_path: str = None, service_name: str = None):
    """
    Create a new game with the provided details.

    Args:
        title: The title of the game (required).
        image_path: Optional path to the game image.
        logo_path: Optional path to the game logo.
        service_name: Optional service name for the game.

    Returns:
        Game: The created game object.

    Raises:
        ValueError: If title is empty or missing.
        IntegrityError: If a game with the same title exists.
    """
    if not title or not title.strip():
        raise ValueError("Game title is required")

    game = Game(
        title=title.strip(),
        image_path=image_path or "/static/games/default_image.png",
        logo_path=logo_path or "/static/games/default_logo.png",
        service_name=service_name
    )

    try:
        db.session.add(game)
        db.session.commit()
        return game
    except IntegrityError:
        db.session.rollback()
        raise ValueError("A game with this title already exists")


def delete_game(game_id: UUID):
    """
    Delete a game by its ID.

    Args:
        game_id: The UUID of the game to delete.

    Returns:
        bool: True if deletion was successful.

    Raises:
        ValueError: If the game is not found or cannot be deleted due to dependencies.
    """
    game = Game.query.get_or_404(game_id)

    if game.tournaments or game.achievements:
        raise ValueError(
            "Cannot delete game with associated tournaments or achievements")

    db.session.delete(game)
    db.session.commit()
    return True


def create_achievement(game_id: UUID, title: str, description: str = None, image_path: str = None):
    """
    Create a new achievement for a game.

    Args:
        game_id: The UUID of the game.
        title: The title of the achievement (required).
        description: Optional description of the achievement.
        image_path: Optional path to the achievement image.

    Returns:
        Achievement: The created achievement object.

    Raises:
        ValueError: If title is empty or game is not found.
        IntegrityError: If an achievement with the same title exists for the game.
    """
    if not title or not title.strip():
        raise ValueError("Achievement title is required")

    game = Game.query.get_or_404(game_id)

    achievement = Achievement(
        title=title.strip(),
        description=description,
        image_path=image_path or "/static/achievements/default_image.png",
        game_id=game.id
    )

    try:
        db.session.add(achievement)
        db.session.commit()
        return achievement
    except IntegrityError:
        db.session.rollback()
        raise ValueError(
            "An achievement with this title already exists for this game")


def assign_achievement_to_user(achievement_id: UUID, user_id: UUID):
    """
    Assign an achievement to a user.

    Args:
        achievement_id: The UUID of the achievement.
        user_id: The UUID of the user.

    Returns:
        Achievement: The assigned achievement object.

    Raises:
        ValueError: If achievement or user is not found, or already assigned.
    """
    achievement = Achievement.query.get_or_404(achievement_id)
    user = User.query.get_or_404(user_id)

    if achievement in user.achievements:
        raise ValueError("Achievement already assigned to this user")

    user.achievements.append(achievement)
    db.session.commit()
    return achievement


def get_user_achievements(user_id: UUID):
    """
    Retrieve all achievements for a user.

    Args:
        user_id: The UUID of the user.

    Returns:
        list: List of Achievement objects.

    Raises:
        ValueError: If user is not found.
    """
    user = User.query.get_or_404(user_id)
    return user.achievements
