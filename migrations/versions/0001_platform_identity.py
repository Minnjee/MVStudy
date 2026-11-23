"""platform identity tables：roles、classes、users、class_members

Revision ID: 0001_platform_identity
Revises:
Create Date: 2026-11-23

本版由 1 号建立全平台迁移历史的第一条。后续票在此之上追加 revision，
已发布的 revision 保持不可变。字段依据 docs/database.md「身份、班级与文件」。
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_platform_identity"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "permissions",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("role_id"),
    )
    op.create_table(
        "classes",
        sa.Column("class_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("class_id"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("login", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role_id", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], name="fk_users_role"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("login", name="uq_users_login"),
    )
    op.create_table(
        "class_members",
        sa.Column("class_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.CheckConstraint("relation IN ('teacher', 'student')", name="ck_class_members_relation"),
        sa.ForeignKeyConstraint(["class_id"], ["classes.class_id"], name="fk_class_members_class"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], name="fk_class_members_user"),
        sa.PrimaryKeyConstraint("class_id", "user_id"),
    )
    op.create_index("ix_class_members_user_id", "class_members", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_class_members_user_id", table_name="class_members")
    op.drop_table("class_members")
    op.drop_table("users")
    op.drop_table("classes")
    op.drop_table("roles")
