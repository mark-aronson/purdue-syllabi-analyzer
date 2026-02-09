"""Pydantic models for the Honors Selective Course rubric analysis."""

from typing import Literal

from pydantic import BaseModel, Field


class ScoredCriterion(BaseModel):
    score: Literal[0, 1]
    rationale: str


class Pillars(BaseModel):
    interdisciplinary_academics: ScoredCriterion
    undergraduate_research: ScoredCriterion
    community_and_global_engagement: ScoredCriterion
    leadership_development: ScoredCriterion


class Rigor(BaseModel):
    advanced_content: ScoredCriterion
    sustained_inquiry: ScoredCriterion
    independent_or_collaborative_work: ScoredCriterion


class StudentAgencyAndResponsibility(BaseModel):
    student_defined_projects: ScoredCriterion
    consequential_decision_making: ScoredCriterion
    extended_analytical_commitment: ScoredCriterion


class DemonstrableEvidenceOfLearning(BaseModel):
    major_project: ScoredCriterion
    portfolio_or_capstone: ScoredCriterion
    public_facing_outcome: ScoredCriterion
    sustained_assessment: ScoredCriterion


class Exclusions(BaseModel):
    lower_division_introductory: ScoredCriterion
    broad_introductory_coverage: ScoredCriterion
    skills_only_or_tool_training: ScoredCriterion
    lacks_major_deliverable: ScoredCriterion
    already_counted: ScoredCriterion


class ReviewDecision(BaseModel):
    decision: Literal["approved", "not_approved", "deferred"]
    rationale: str


class CourseInformation(BaseModel):
    course_number: str | None = None
    course_title: str | None = None
    department: str | None = None
    college: str | None = None
    review_date: str | None = None


class CourseAnalysis(BaseModel):
    pillars: Pillars
    rigor: Rigor
    student_agency_and_responsibility: StudentAgencyAndResponsibility
    demonstrable_evidence_of_learning: DemonstrableEvidenceOfLearning
    exclusions: Exclusions
    review_decision: ReviewDecision


class SyllabusReview(BaseModel):
    course_information: CourseInformation
    course_analysis: CourseAnalysis
