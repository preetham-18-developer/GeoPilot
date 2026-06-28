/**
 * uiAudit.ts
 *
 * A TypeScript data integrity auditor utility for the frontend.
 * Validates API responses, page state, component filters, and rendering.
 */

export interface AuditResult {
  passed: boolean;
  score: number; // 0 to 100
  errors: string[];
  warnings: string[];
}

export class UIDataIntegrityAuditor {
  /**
   * Validates the question and keyword validation report payload.
   */
  public static auditValidationReport(payload: any): AuditResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    let score = 100;

    if (!payload) {
      return { passed: false, score: 0, errors: ["Payload is null or undefined."], warnings };
    }

    // Required top-level keys
    const requiredKeys = ["project_id", "overall_status", "combined_quality_score", "question_audit", "keyword_audit"];
    for (const key of requiredKeys) {
      if (!(key in payload)) {
        errors.push(`Missing top-level key: ${key}`);
        score -= 20;
      }
    }

    if (errors.length > 0) {
      return { passed: false, score: Math.max(0, score), errors, warnings };
    }

    // Audit question_audit section
    const qa = payload.question_audit;
    if (qa) {
      const requiredQAKeys = [
        "total_questions", "quality_score", "uniqueness_score", 
        "duplicate_count", "missing_answers", "category_diversity", 
        "template_violations", "confidence_health", "warnings", "suggestions"
      ];
      for (const key of requiredQAKeys) {
        if (!(key in qa)) {
          errors.push(`Missing key in question_audit: ${key}`);
          score -= 5;
        }
      }
      
      if (qa.missing_answers > 0) {
        warnings.push(`Found ${qa.missing_answers} questions with missing answers in the audit.`);
        score -= 10;
      }
      if (qa.duplicate_count > 0) {
        warnings.push(`Found ${qa.duplicate_count} duplicate question pairs.`);
        score -= 10;
      }
    }

    // Audit keyword_audit section
    const kwa = payload.keyword_audit;
    if (kwa) {
      const requiredKWAKeys = [
        "total_keywords", "quality_score", "uniqueness_score", 
        "stem_duplication", "category_saturation", "intent_coverage", 
        "missing_clusters", "priority_health", "warnings", "suggestions"
      ];
      for (const key of requiredKWAKeys) {
        if (!(key in kwa)) {
          errors.push(`Missing key in keyword_audit: ${key}`);
          score -= 5;
        }
      }

      if (kwa.stem_duplication && kwa.stem_duplication.rate > 0.25) {
        warnings.push(`High stem duplication rate of ${(kwa.stem_duplication.rate * 100).toFixed(0)}% detected.`);
        score -= 5;
      }
    }

    return {
      passed: errors.length === 0 && score >= 70,
      score: Math.max(0, score),
      errors,
      warnings,
    };
  }

  /**
   * Audits Business Intelligence payload.
   */
  public static auditBusinessProfile(payload: any): AuditResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    let score = 100;

    if (!payload) {
      return { passed: false, score: 0, errors: ["Business profile payload is empty."], warnings };
    }

    const requiredFields = ["company_name", "industry", "description", "mission", "vision", "usp", "target_audience"];
    for (const field of requiredFields) {
      if (!payload[field] || payload[field] === "N/A" || payload[field] === "NOT FOUND") {
        errors.push(`Missing or invalid critical profile field: ${field}`);
        score -= 15;
      }
    }

    return {
      passed: errors.length === 0,
      score: Math.max(0, score),
      errors,
      warnings,
    };
  }

  /**
   * Run UI integrity check cases (mock unit tests).
   */
  public static runSuite(): { name: string; result: AuditResult }[] {
    const suiteResults = [];

    // Test case 1: Happy Path Validation Payload
    const happyPayload = {
      project_id: "test-proj-123",
      overall_status: "healthy",
      combined_quality_score: 95.0,
      question_audit: {
        total_questions: 10,
        quality_score: 96,
        uniqueness_score: 100,
        duplicate_count: 0,
        missing_answers: 0,
        category_diversity: { unique_categories: 3, ratio: 0.7 },
        template_violations: [],
        confidence_health: { low_confidence_count: 0 },
        warnings: [],
        suggestions: []
      },
      keyword_audit: {
        total_keywords: 15,
        quality_score: 94,
        uniqueness_score: 100,
        stem_duplication: { rate: 0.1, top_stems: [] },
        category_saturation: { saturated: false },
        intent_coverage: { unique_count: 3, present: ["informational", "transactional"] },
        missing_clusters: 0,
        priority_health: { high_count: 5 },
        warnings: [],
        suggestions: []
      }
    };
    suiteResults.push({
      name: "Happy Path Validation Audit",
      result: this.auditValidationReport(happyPayload)
    });

    // Test case 2: Mismatched/Degraded Payload
    const degradedPayload = {
      project_id: "test-proj-456",
      overall_status: "warning",
      combined_quality_score: 55.0,
      question_audit: {
        total_questions: 5,
        quality_score: 60,
        uniqueness_score: 60,
        duplicate_count: 2,
        missing_answers: 1,
        category_diversity: { unique_categories: 1, ratio: 0.2 },
        template_violations: ["Question doesn't end with question mark"],
        confidence_health: { low_confidence_count: 1 },
        warnings: ["Duplicate questions found"],
        suggestions: []
      },
      keyword_audit: {
        total_keywords: 6,
        quality_score: 50,
        uniqueness_score: 50,
        stem_duplication: { rate: 0.4, top_stems: ["seo"] },
        category_saturation: { saturated: true },
        intent_coverage: { unique_count: 1, present: ["informational"] },
        missing_clusters: 2,
        priority_health: { high_count: 0 },
        warnings: [],
        suggestions: []
      }
    };
    suiteResults.push({
      name: "Degraded Path Validation Audit",
      result: this.auditValidationReport(degradedPayload)
    });

    return suiteResults;
  }
}
