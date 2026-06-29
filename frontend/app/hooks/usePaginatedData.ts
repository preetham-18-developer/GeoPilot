"use client";

import { useState, useCallback } from "react";
import { API_BASE, authHeader } from "../lib/config";

export function useQuestions(userId: string) {
  const [questionsPage, setQuestionsPage] = useState(1);
  const [questionsData, setQuestionsData] = useState<any[]>([]);
  const [questionsTotalCount, setQuestionsTotalCount] = useState(0);
  const [questionsLoading, setQuestionsLoading] = useState(false);
  const [questionSearch, setQuestionSearch] = useState("");
  const [questionTypeFilter, setQuestionTypeFilter] = useState("All");
  const [questionsSortBy, setQuestionsSortBy] = useState("priority_score");
  const [questionsSortOrder, setQuestionsSortOrder] = useState("desc");

  const fetchQuestions = useCallback(
    async (
      projectId: string,
      page: number,
      search: string,
      typeFilter: string,
      sortBy: string,
      sortOrder: string
    ) => {
      setQuestionsLoading(true);
      try {
        const params = new URLSearchParams({
          page: String(page),
          page_size: "10",
          search,
          question_type: typeFilter,
          sort_by: sortBy,
          sort_order: sortOrder,
        });
        const res = await fetch(`${API_BASE}/analysis/questions/${projectId}?${params}`, {
          headers: authHeader(userId),
        });
        if (res.ok) {
          const data = await res.json();
          setQuestionsData(data.questions ?? []);
          setQuestionsTotalCount(data.total_count ?? 0);
        }
      } catch (err) {
        console.error("Error fetching questions:", err);
      } finally {
        setQuestionsLoading(false);
      }
    },
    [userId]
  );

  const resetQuestions = useCallback(() => {
    setQuestionsPage(1);
    setQuestionsData([]);
    setQuestionsTotalCount(0);
    setQuestionSearch("");
    setQuestionTypeFilter("All");
  }, []);

  return {
    questionsPage, setQuestionsPage,
    questionsData,
    questionsTotalCount,
    questionsLoading,
    questionSearch, setQuestionSearch,
    questionTypeFilter, setQuestionTypeFilter,
    questionsSortBy, setQuestionsSortBy,
    questionsSortOrder, setQuestionsSortOrder,
    fetchQuestions,
    resetQuestions,
  };
}

export function useKeywords(userId: string) {
  const [keywordsPage, setKeywordsPage] = useState(1);
  const [keywordsData, setKeywordsData] = useState<any[]>([]);
  const [keywordsTotalCount, setKeywordsTotalCount] = useState(0);
  const [keywordsLoading, setKeywordsLoading] = useState(false);
  const [keywordSearch, setKeywordSearch] = useState("");
  const [keywordClusterFilter, setKeywordClusterFilter] = useState("All");
  const [keywordsSortBy, setKeywordsSortBy] = useState("keyword");
  const [keywordsSortOrder, setKeywordsSortOrder] = useState("asc");

  const fetchKeywords = useCallback(
    async (
      projectId: string,
      page: number,
      search: string,
      typeFilter: string,
      sortBy: string,
      sortOrder: string
    ) => {
      setKeywordsLoading(true);
      try {
        const params = new URLSearchParams({
          page_size: "10",
          page: String(page),
          search,
          keyword_type: typeFilter,
          sort_by: sortBy,
          sort_order: sortOrder,
        });
        const res = await fetch(`${API_BASE}/analysis/keywords/${projectId}?${params}`, {
          headers: authHeader(userId),
        });
        if (res.ok) {
          const data = await res.json();
          const rawKeywords = data.keywords ?? [];
          
          // Map to UI-expected format to support both the projects/keywords and old formats
          const mapped = rawKeywords.map((kw: any) => ({
            id: kw.id || kw.keyword,
            keyword_text: kw.keyword || kw.keyword_text || "",
            category: kw.keyword_type || kw.category || "PRIMARY",
            search_intent: kw.intent || kw.search_intent || "informational",
            clustering_theme: kw.cluster || kw.clustering_theme || "General",
            priority: kw.priority || "Medium",
            difficulty_estimate: kw.difficulty_estimate || "Medium",
            opportunity_estimate: kw.opportunity_estimate || "Medium",
            source: kw.source || "Recommendation Queries",
            confidence_score: kw.confidence_score !== undefined ? kw.confidence_score : (kw.frequency ? kw.frequency / 100 : 0.45)
          }));
          
          setKeywordsData(mapped);
          setKeywordsTotalCount(data.total ?? data.total_count ?? 0);
        }
      } catch (err) {
        console.error("Error fetching keywords:", err);
      } finally {
        setKeywordsLoading(false);
      }
    },
    [userId]
  );

  const resetKeywords = useCallback(() => {
    setKeywordsPage(1);
    setKeywordsData([]);
    setKeywordsTotalCount(0);
    setKeywordSearch("");
    setKeywordClusterFilter("All");
  }, []);

  return {
    keywordsPage, setKeywordsPage,
    keywordsData,
    keywordsTotalCount,
    keywordsLoading,
    keywordSearch, setKeywordSearch,
    keywordClusterFilter, setKeywordClusterFilter,
    keywordsSortBy, setKeywordsSortBy,
    keywordsSortOrder, setKeywordsSortOrder,
    fetchKeywords,
    resetKeywords,
  };
}
