"""Delete-current-user endpoint tests."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.routers.auth import delete_me


def test_delete_me_removes_user_and_notebook_storage():
    user_id = uuid4()
    nb1 = uuid4()
    nb2 = uuid4()

    current_user = MagicMock()
    current_user.id = user_id

    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.all.return_value = [(nb1,), (nb2,)]
    db.query.return_value = query

    with (
        patch("app.routers.auth.shutil.rmtree") as rmtree,
        patch("app.routers.auth.STORAGE_DIR") as storage_dir,
    ):
        dir1 = MagicMock()
        dir1.is_dir.return_value = True
        dir2 = MagicMock()
        dir2.is_dir.return_value = False
        storage_dir.__truediv__.return_value.__truediv__.side_effect = [dir1, dir2]

        delete_me(db=db, current_user=current_user)

    db.delete.assert_called_once_with(current_user)
    db.commit.assert_called_once()
    rmtree.assert_called_once_with(dir1)


def test_delete_me_skips_missing_storage():
    current_user = MagicMock()
    current_user.id = uuid4()

    db = MagicMock()
    query = MagicMock()
    query.filter.return_value.all.return_value = [(uuid4(),)]
    db.query.return_value = query

    with (
        patch("app.routers.auth.shutil.rmtree") as rmtree,
        patch("app.routers.auth.STORAGE_DIR") as storage_dir,
    ):
        missing = MagicMock()
        missing.is_dir.return_value = False
        storage_dir.__truediv__.return_value.__truediv__.return_value = missing

        delete_me(db=db, current_user=current_user)

    db.delete.assert_called_once_with(current_user)
    db.commit.assert_called_once()
    rmtree.assert_not_called()
