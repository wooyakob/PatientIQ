import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, BookOpen, ExternalLink, Send, Loader2, Star, Search, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  getPatientResearch,
  askResearchQuestion,
  saveResearchAnswer,
  updateAnswerRating,
  searchTavilyResearch,
  addResearchPaper,
  ResearchResult,
  ResearchPaper
} from '@/lib/api';
import { Textarea } from '@/components/ui/textarea';

interface ResearchAnswer {
  question: string;
  answer: string;
  papers: any[];
  answerId?: string;
  rating?: number;
}

const ResearchDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';
  const [question, setQuestion] = useState('');
  const [answers, setAnswers] = useState<ResearchAnswer[]>([]);
  const [tavilyQuery, setTavilyQuery] = useState('');
  const [tavilyResults, setTavilyResults] = useState<ResearchPaper[]>([]);
  const [selectedPaper, setSelectedPaper] = useState<ResearchPaper | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Fetch initial research summary
  const {
    data: initialResearch,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['research', patientId],
    queryFn: () => getPatientResearch(patientId),
    enabled: Boolean(patientId),
  });

  // Mutation for asking custom questions
  const askMutation = useMutation({
    mutationFn: (q: string) => askResearchQuestion(patientId, q),
    onSuccess: (data) => {
      // Add answer to the list instead of replacing
      const newAnswer: ResearchAnswer = {
        question: data.question,
        answer: data.answer,
        papers: data.papers || [],
      };

      // Clear question field immediately so user can type another
      setQuestion('');

      // Add to answers list immediately using function form to avoid stale closure
      setAnswers((prevAnswers) => [newAnswer, ...prevAnswers]);

      // Save to database in background (don't await)
      saveResearchAnswer(data.question, data.answer)
        .then((result) => {
          // Update the answer with the ID once saved
          setAnswers((prev) =>
            prev.map((a) =>
              a.question === data.question && !a.answerId
                ? { ...a, answerId: result.answer_id }
                : a
            )
          );
        })
        .catch((err) => {
          console.error('Failed to save answer:', err);
        });
    },
  });

  // Mutation for rating answers
  const ratingMutation = useMutation({
    mutationFn: ({ answerId, rating }: { answerId: string; rating: number }) =>
      updateAnswerRating(answerId, rating),
    onSuccess: (data, variables) => {
      // Update local state using function form to avoid stale closure
      setAnswers((prevAnswers) =>
        prevAnswers.map((a) =>
          a.answerId === variables.answerId ? { ...a, rating: variables.rating } : a
        )
      );
    },
  });

  // Mutation for Tavily search
  const tavilySearchMutation = useMutation({
    mutationFn: (query: string) => searchTavilyResearch(query),
    onSuccess: (data) => {
      setTavilyResults(data.results || []);
      setTavilyQuery('');
    },
  });

  // Mutation for adding papers to database
  const addPaperMutation = useMutation({
    mutationFn: (paper: ResearchPaper) => addResearchPaper(paper),
    onSuccess: () => {
      setShowAddModal(false);
      setSelectedPaper(null);
      alert('Paper added to database successfully!');
    },
    onError: (error: any) => {
      alert(error.message || 'Failed to add paper');
    },
  });

  const handleAskQuestion = () => {
    if (question.trim()) {
      askMutation.mutate(question.trim());
    }
  };

  const handleRating = (answerId: string | undefined, rating: number) => {
    if (!answerId) return;
    ratingMutation.mutate({ answerId, rating });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading research…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load research</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!initialResearch) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">No research available</h1>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-4xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate(`/patient/${patientId}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to {initialResearch.patient_name}</span>
        </button>

        <div className="glass-card p-8 animate-slide-up">
          {/* Header */}
          <div className="flex items-center gap-4 mb-6">
            <div className="neo-card p-3 rounded-xl">
              <BookOpen className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Medical Research</h1>
              <p className="text-muted-foreground">Relevant to {initialResearch.patient_name}'s condition</p>
            </div>
          </div>

          {/* Condition Badge */}
          <div className="neo-card p-6 rounded-2xl mb-8">
            <h2 className="text-xl font-semibold text-primary mb-2">
              {initialResearch.condition} Research
            </h2>
            <p className="text-sm text-muted-foreground">
              Based on: {initialResearch.condition}
            </p>
          </div>

          {/* Clinical Summary - Initial Research */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-foreground mb-4">Clinical Summary</h3>
            <div className="space-y-4">
              {initialResearch.answer.split('\n\n').map((paragraph, index) => (
                <div
                  key={index}
                  className="animate-slide-up"
                  style={{ animationDelay: `${(index + 1) * 100}ms` }}
                >
                  <p className="text-foreground leading-relaxed">{paragraph}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Research Papers */}
          {initialResearch.papers && initialResearch.papers.length > 0 && (
            <div className="mb-8 pt-6 border-t border-border">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Referenced Research Papers ({initialResearch.papers.length})
              </h3>
              <div className="space-y-4">
                {initialResearch.papers.map((paper, index) => (
                  <div
                    key={index}
                    className="neo-card p-4 rounded-xl animate-slide-up"
                    style={{ animationDelay: `${(index + 4) * 100}ms` }}
                  >
                    <h4 className="font-medium text-foreground mb-2">{paper.title}</h4>
                    {paper.author && (
                      <p className="text-sm text-muted-foreground mb-1">
                        Authors: {paper.author}
                      </p>
                    )}
                    {paper.article_citation && (
                      <p className="text-sm text-muted-foreground mb-2">
                        Citation: {paper.article_citation}
                      </p>
                    )}
                    {paper.pmc_link && (
                      <a
                        href={paper.pmc_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        View full paper
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Ask a Question Section */}
          <div className="pt-6 border-t border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">
              Ask a Clinical Question
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Ask a specific question about {initialResearch.condition} management, treatment options, or evidence-based approaches.
            </p>
            <div className="space-y-4">
              <Textarea
                placeholder="e.g., What are the latest treatment guidelines for managing acute exacerbations?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="min-h-[100px] resize-none"
                disabled={askMutation.isPending}
              />
              <Button
                onClick={handleAskQuestion}
                disabled={!question.trim() || askMutation.isPending}
                className="w-full sm:w-auto"
              >
                {askMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Searching research...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Ask Question
                  </>
                )}
              </Button>
              {askMutation.isError && (
                <p className="text-sm text-destructive">
                  Error: {(askMutation.error as Error).message}
                </p>
              )}
            </div>
          </div>

          {/* Search Latest Research (Web) */}
          <div className="pt-6 border-t border-border">
            <div className="flex items-center gap-2 mb-2">
              <Search className="h-5 w-5" />
              <h3 className="text-xl font-semibold">Search Latest Research (Web)</h3>
            </div>
            <p className="text-sm text-muted-foreground mb-4">
              Search the web for the latest research on {initialResearch.condition}
            </p>

            <div className="space-y-4">
              <Textarea
                placeholder={`e.g., "Latest clinical trials for ${initialResearch.condition} 2025"`}
                value={tavilyQuery}
                onChange={(e) => setTavilyQuery(e.target.value)}
                rows={2}
              />
              <Button
                onClick={() => tavilySearchMutation.mutate(tavilyQuery)}
                disabled={!tavilyQuery.trim() || tavilySearchMutation.isPending}
              >
                <Search className="h-4 w-4 mr-2" />
                {tavilySearchMutation.isPending ? 'Searching...' : 'Search Web'}
              </Button>
            </div>

            {/* Tavily Results */}
            {tavilyResults.length > 0 && (
              <div className="mt-6 space-y-4">
                <h4 className="text-lg font-medium">Web Results ({tavilyResults.length})</h4>
                {tavilyResults.map((paper, idx) => (
                  <div key={idx} className="neo-card p-4 space-y-3">
                    <h5 className="font-semibold text-base">{paper.title}</h5>
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {paper.article_text}
                    </p>
                    <div className="flex items-center gap-3 text-sm">
                      <a
                        href={paper.pmc_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        View Source →
                      </a>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedPaper(paper);
                          setShowAddModal(true);
                        }}
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Add to Database
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Previous Answers Section */}
          {answers.length > 0 && (
            <div className="mt-8 pt-6 border-t border-border space-y-6">
              <h3 className="text-lg font-semibold text-foreground">Previous Questions & Answers</h3>
              {answers.map((answer, idx) => (
                <div
                  key={idx}
                  className="neo-card p-6 rounded-2xl space-y-4 animate-slide-up"
                >
                  {/* Question */}
                  <div>
                    <p className="text-sm font-medium text-primary mb-2">Question:</p>
                    <p className="text-foreground">{answer.question}</p>
                  </div>

                  {/* Answer */}
                  <div>
                    <p className="text-sm font-medium text-primary mb-2">Answer:</p>
                    <div className="space-y-3">
                      {answer.answer.split('\n\n').map((paragraph, pIdx) => (
                        <p key={pIdx} className="text-foreground leading-relaxed">
                          {paragraph}
                        </p>
                      ))}
                    </div>
                  </div>

                  {/* Referenced Papers */}
                  {answer.papers && answer.papers.length > 0 && (
                    <div className="pt-4 border-t border-border/50">
                      <p className="text-sm font-medium text-muted-foreground mb-3">
                        Referenced Papers:
                      </p>
                      <div className="space-y-2">
                        {answer.papers.map((paper, pIdx) => (
                          <div key={pIdx} className="text-sm">
                            <p className="font-medium text-foreground">{paper.title}</p>
                            {paper.pmc_link && (
                              <a
                                href={paper.pmc_link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                              >
                                <ExternalLink className="h-3 w-3" />
                                View paper
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Rating */}
                  <div className="pt-4 border-t border-border/50">
                    <p className="text-sm font-medium text-muted-foreground mb-2">
                      Rate this answer:
                    </p>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => handleRating(answer.answerId, star)}
                          disabled={!answer.answerId || ratingMutation.isPending}
                          className="p-1 hover:scale-110 transition-transform disabled:opacity-50"
                        >
                          <Star
                            className={`h-5 w-5 ${
                              (answer.rating ?? 0) >= star
                                ? 'fill-yellow-400 text-yellow-400'
                                : 'text-muted-foreground'
                            }`}
                          />
                        </button>
                      ))}
                      {answer.rating && (
                        <span className="ml-2 text-sm text-muted-foreground">
                          {answer.rating}/5
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-border">
            <p className="text-xs text-muted-foreground flex items-center gap-2">
              <ExternalLink className="h-3.5 w-3.5" />
              Research summaries generated from peer-reviewed medical literature using semantic vector search
            </p>
          </div>
        </div>
      </main>

      {/* Add Paper Confirmation Modal */}
      {showAddModal && selectedPaper && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background p-6 rounded-lg shadow-lg max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-3">Add Paper to Database</h3>
            <p className="text-sm text-muted-foreground mb-2">
              <strong>{selectedPaper.title}</strong>
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              This will add the paper to the medical research database and vectorize
              it for future semantic searches.
            </p>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowAddModal(false);
                  setSelectedPaper(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={() => addPaperMutation.mutate(selectedPaper)}
                disabled={addPaperMutation.isPending}
              >
                {addPaperMutation.isPending ? 'Adding...' : 'Add Paper'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResearchDetail;
