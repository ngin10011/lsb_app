"""add auftrag_id to rechnung (1-n)"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '87aae988e92c'          # <- aus dem Dateinamen
down_revision = '5113d4e8aa62'     # <- deine vorherige Revision (steht in 'flask db history')
branch_labels = None
depends_on = None



def upgrade():
    with op.batch_alter_table('rechnung', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auftrag_id', sa.Integer(), nullable=False))
        batch_op.create_index('ix_rechnung_auftrag_id', ['auftrag_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_rechnung_auftrag',    # <- Name ist bei SQLite wichtig!
            referent_table='auftrag',
            local_cols=['auftrag_id'],
            remote_cols=['id'],
            ondelete='CASCADE'
        )

def downgrade():
    with op.batch_alter_table('rechnung', schema=None) as batch_op:
        batch_op.drop_constraint('fk_rechnung_auftrag', type_='foreignkey')
        batch_op.drop_index('ix_rechnung_auftrag_id')
        batch_op.drop_column('auftrag_id')
