"""Начальная схема базы данных.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'projects' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('projects')}
        missing = sorted(set(('id', 'title', 'age_group', 'icd_codes', 'organization', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table projects is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'checklist_answers' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('checklist_answers')}
        missing = sorted(set(('id', 'project_id', 'item_id', 'response', 'comment', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table checklist_answers is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'conflicts' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('conflicts')}
        missing = sorted(set(('id', 'project_id', 'card_ids', 'description', 'status', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table conflicts is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'documents' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('documents')}
        missing = sorted(set(('id', 'project_id', 'filename', 'stored_path', 'status', 'status_detail', 'page_count', 'biblio', 'study_design', 'content_hash', 'duplicate_of_id', 'relevance', 'relevance_reason', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table documents is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'expert_edits' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('expert_edits')}
        missing = sorted(set(('id', 'project_id', 'entity_type', 'entity_id', 'field', 'old_value', 'new_value', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table expert_edits is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'quality_criteria' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('quality_criteria')}
        missing = sorted(set(('id', 'project_id', 'text', 'thesis_ids', 'review_status', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table quality_criteria is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'theses' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('theses')}
        missing = sorted(set(('id', 'project_id', 'section', 'text', 'provenance', 'comment', 'udd', 'uur', 'subsection_title', 'direction', 'strength_phrase', 'intervention', 'evidence_backed_core', 'expert_additions', 'grade_rationale', 'consensus', 'quality_criterion', 'review_flags', 'review_status', 'auto_data', 'user_edits', 'pending_version', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table theses is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'evidence_cards' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('evidence_cards')}
        missing = sorted(set(('id', 'project_id', 'document_id', 'page_number', 'subject', 'predicate', 'object_', 'negation', 'intervention_type', 'udd_source', 'extraction_confidence', 'kr_section', 'statement_ru', 'card_type', 'population', 'intervention', 'outcome', 'conditions', 'polarity', 'quote', 'quote_verified', 'meaning_verified', 'problems', 'review_status', 'merged_into_id', 'content_hash', 'auto_data', 'user_edits', 'pending_version', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table evidence_cards is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'jobs' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('jobs')}
        missing = sorted(set(('id', 'kind', 'document_id', 'status', 'error', 'started_at', 'finished_at', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table jobs is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'pages' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('pages')}
        missing = sorted(set(('id', 'document_id', 'number', 'text', 'status', 'error')) - present)
        if missing:
            raise RuntimeError(
                "Existing table pages is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'llm_calls' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('llm_calls')}
        missing = sorted(set(('id', 'job_id', 'document_id', 'step', 'model', 'input_tokens', 'output_tokens', 'cost_usd', 'seconds', 'created_at')) - present)
        if missing:
            raise RuntimeError(
                "Existing table llm_calls is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'thesis_cards' in existing_tables:
        present = {column["name"] for column in sa.inspect(op.get_bind()).get_columns('thesis_cards')}
        missing = sorted(set(('thesis_id', 'card_id')) - present)
        if missing:
            raise RuntimeError(
                "Existing table thesis_cards is missing columns: " + ", ".join(sorted(missing))
                + ". Back up the database and add a migration for this schema before starting the API."
            )
    if 'projects' not in existing_tables:
        op.create_table(
            'projects',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('age_group', sa.String(64), nullable=False),
            sa.Column('icd_codes', sa.JSON(), nullable=False),
            sa.Column('organization', sa.String(255), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('projects')

    if 'checklist_answers' not in existing_tables:
        op.create_table(
            'checklist_answers',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.String(16), nullable=False),
            sa.Column('response', sa.String(24), nullable=False),
            sa.Column('comment', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('project_id', 'item_id')
        )
        existing_tables.add('checklist_answers')

    if 'conflicts' not in existing_tables:
        op.create_table(
            'conflicts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('card_ids', sa.JSON(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('status', sa.String(16), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('conflicts')

    if 'documents' not in existing_tables:
        op.create_table(
            'documents',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('filename', sa.String(255), nullable=False),
            sa.Column('stored_path', sa.String(512), nullable=False),
            sa.Column('status', sa.String(32), nullable=False),
            sa.Column('status_detail', sa.Text(), nullable=True),
            sa.Column('page_count', sa.Integer(), nullable=True),
            sa.Column('biblio', sa.JSON(), nullable=True),
            sa.Column('study_design', sa.String(32), nullable=True),
            sa.Column('content_hash', sa.String(64), nullable=True),
            sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
            sa.Column('relevance', sa.String(16), nullable=False),
            sa.Column('relevance_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['duplicate_of_id'], ['documents.id']),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('documents')

    if 'expert_edits' not in existing_tables:
        op.create_table(
            'expert_edits',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('entity_type', sa.String(32), nullable=False),
            sa.Column('entity_id', sa.Integer(), nullable=False),
            sa.Column('field', sa.String(64), nullable=False),
            sa.Column('old_value', sa.JSON(), nullable=True),
            sa.Column('new_value', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('expert_edits')

    if 'quality_criteria' not in existing_tables:
        op.create_table(
            'quality_criteria',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('thesis_ids', sa.JSON(), nullable=False),
            sa.Column('review_status', sa.String(16), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('quality_criteria')

    if 'theses' not in existing_tables:
        op.create_table(
            'theses',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('section', sa.String(32), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('provenance', sa.String(24), nullable=False),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('udd', sa.Integer(), nullable=True),
            sa.Column('uur', sa.String(8), nullable=True),
            sa.Column('subsection_title', sa.String(255), nullable=True),
            sa.Column('direction', sa.String(16), nullable=True),
            sa.Column('strength_phrase', sa.String(64), nullable=True),
            sa.Column('intervention', sa.JSON(), nullable=True),
            sa.Column('evidence_backed_core', sa.Text(), nullable=True),
            sa.Column('expert_additions', sa.JSON(), nullable=False),
            sa.Column('grade_rationale', sa.Text(), nullable=True),
            sa.Column('consensus', sa.JSON(), nullable=True),
            sa.Column('quality_criterion', sa.JSON(), nullable=True),
            sa.Column('review_flags', sa.JSON(), nullable=False),
            sa.Column('review_status', sa.String(16), nullable=False),
            sa.Column('auto_data', sa.JSON(), nullable=True),
            sa.Column('user_edits', sa.JSON(), nullable=True),
            sa.Column('pending_version', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('theses')

    if 'evidence_cards' not in existing_tables:
        op.create_table(
            'evidence_cards',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('project_id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('page_number', sa.Integer(), nullable=False),
            sa.Column('subject', sa.Text(), nullable=True),
            sa.Column('predicate', sa.Text(), nullable=True),
            sa.Column('object_', sa.Text(), nullable=True),
            sa.Column('negation', sa.Boolean(), nullable=False),
            sa.Column('intervention_type', sa.String(16), nullable=True),
            sa.Column('udd_source', sa.Integer(), nullable=True),
            sa.Column('extraction_confidence', sa.Float(), nullable=True),
            sa.Column('kr_section', sa.String(8), nullable=True),
            sa.Column('statement_ru', sa.Text(), nullable=False),
            sa.Column('card_type', sa.String(16), nullable=False),
            sa.Column('population', sa.Text(), nullable=True),
            sa.Column('intervention', sa.Text(), nullable=True),
            sa.Column('outcome', sa.Text(), nullable=True),
            sa.Column('conditions', sa.Text(), nullable=True),
            sa.Column('polarity', sa.String(16), nullable=False),
            sa.Column('quote', sa.Text(), nullable=False),
            sa.Column('quote_verified', sa.String(16), nullable=False),
            sa.Column('meaning_verified', sa.String(16), nullable=False),
            sa.Column('problems', sa.JSON(), nullable=False),
            sa.Column('review_status', sa.String(16), nullable=False),
            sa.Column('merged_into_id', sa.Integer(), nullable=True),
            sa.Column('content_hash', sa.String(64), nullable=False),
            sa.Column('auto_data', sa.JSON(), nullable=False),
            sa.Column('user_edits', sa.JSON(), nullable=True),
            sa.Column('pending_version', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id']),
            sa.ForeignKeyConstraint(['merged_into_id'], ['evidence_cards.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('evidence_cards')

    if 'jobs' not in existing_tables:
        op.create_table(
            'jobs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('kind', sa.String(32), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('status', sa.String(16), nullable=False),
            sa.Column('error', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('finished_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('jobs')

    if 'pages' not in existing_tables:
        op.create_table(
            'pages',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('number', sa.Integer(), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('status', sa.String(16), nullable=False),
            sa.Column('error', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('pages')

    if 'llm_calls' not in existing_tables:
        op.create_table(
            'llm_calls',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('job_id', sa.Integer(), nullable=True),
            sa.Column('document_id', sa.Integer(), nullable=True),
            sa.Column('step', sa.String(32), nullable=False),
            sa.Column('model', sa.String(128), nullable=False),
            sa.Column('input_tokens', sa.Integer(), nullable=False),
            sa.Column('output_tokens', sa.Integer(), nullable=False),
            sa.Column('cost_usd', sa.Float(), nullable=True),
            sa.Column('seconds', sa.Float(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['job_id'], ['jobs.id']),
            sa.ForeignKeyConstraint(['document_id'], ['documents.id']),
            sa.PrimaryKeyConstraint('id')
        )
        existing_tables.add('llm_calls')

    if 'thesis_cards' not in existing_tables:
        op.create_table(
            'thesis_cards',
            sa.Column('thesis_id', sa.Integer(), nullable=False),
            sa.Column('card_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['card_id'], ['evidence_cards.id']),
            sa.ForeignKeyConstraint(['thesis_id'], ['theses.id']),
            sa.PrimaryKeyConstraint('thesis_id', 'card_id')
        )
        existing_tables.add('thesis_cards')
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('checklist_answers')}
    if 'ix_checklist_answers_project_id' not in indexes:
        op.create_index('ix_checklist_answers_project_id', 'checklist_answers', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('conflicts')}
    if 'ix_conflicts_project_id' not in indexes:
        op.create_index('ix_conflicts_project_id', 'conflicts', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('documents')}
    if 'ix_documents_content_hash' not in indexes:
        op.create_index('ix_documents_content_hash', 'documents', ['content_hash'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('documents')}
    if 'ix_documents_project_id' not in indexes:
        op.create_index('ix_documents_project_id', 'documents', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('expert_edits')}
    if 'ix_expert_edits_project_id' not in indexes:
        op.create_index('ix_expert_edits_project_id', 'expert_edits', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('quality_criteria')}
    if 'ix_quality_criteria_project_id' not in indexes:
        op.create_index('ix_quality_criteria_project_id', 'quality_criteria', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('theses')}
    if 'ix_theses_project_id' not in indexes:
        op.create_index('ix_theses_project_id', 'theses', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('evidence_cards')}
    if 'ix_evidence_cards_content_hash' not in indexes:
        op.create_index('ix_evidence_cards_content_hash', 'evidence_cards', ['content_hash'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('evidence_cards')}
    if 'ix_evidence_cards_document_id' not in indexes:
        op.create_index('ix_evidence_cards_document_id', 'evidence_cards', ['document_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('evidence_cards')}
    if 'ix_evidence_cards_project_id' not in indexes:
        op.create_index('ix_evidence_cards_project_id', 'evidence_cards', ['project_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('jobs')}
    if 'ix_jobs_status' not in indexes:
        op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('pages')}
    if 'ix_pages_document_id' not in indexes:
        op.create_index('ix_pages_document_id', 'pages', ['document_id'], unique=False)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes('llm_calls')}
    if 'ix_llm_calls_document_id' not in indexes:
        op.create_index('ix_llm_calls_document_id', 'llm_calls', ['document_id'], unique=False)


def downgrade():
    op.drop_table('thesis_cards')
    op.drop_table('llm_calls')
    op.drop_table('pages')
    op.drop_table('jobs')
    op.drop_table('evidence_cards')
    op.drop_table('theses')
    op.drop_table('quality_criteria')
    op.drop_table('expert_edits')
    op.drop_table('documents')
    op.drop_table('conflicts')
    op.drop_table('checklist_answers')
    op.drop_table('projects')
