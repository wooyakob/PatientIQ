import { useState } from 'react';
import { Send, Bot, AlertTriangle, TrendingUp, Users, FileText, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface WearableAlert {
  metric: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  priority: number;
  message: string;
  values?: number[];
  threshold?: number;
  clinical_significance: string;
}

interface SimilarPatient {
  patient_id: string;
  patient_name: string;
  similarity_score: number;
  matching_criteria: string[];
}

interface ResearchPaper {
  title: string;
  author: string;
  article_citation?: string;
  pmc_link?: string;
  relevance_score?: number;
  key_findings?: string[];
}

interface AnalyticsResponse {
  patient_id: string;
  patient_name: string;
  patient_condition: string;
  question: string;
  alerts: WearableAlert[];
  similar_patients?: SimilarPatient[];
  research_papers?: ResearchPaper[];
  recommendations?: string[];
  answer: string;
  generated_at: string;
  analysis_duration_seconds?: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  analysis?: AnalyticsResponse;
  timestamp: Date;
}

interface WearableAnalyticsChatProps {
  patientId: string;
  patientName: string;
}

export function WearableAnalyticsChat({ patientId, patientName }: WearableAnalyticsChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const analyzeWearables = async (question: string) => {
    setIsLoading(true);
    
    try {
      const response = await fetch(`http://localhost:8000/api/patients/${patientId}/wearables/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_id: patientId,
          question: question,
          days: 30,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to analyze: ${response.statusText}`);
      }

      const data: AnalyticsResponse = await response.json();
      return data;
    } catch (error) {
      console.error('Error analyzing wearables:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const analysis = await analyzeWearables(userMessage.content);
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: analysis.answer,
        analysis: analysis,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error analyzing the wearable data. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'medium': return 'bg-yellow-500 text-black';
      case 'low': return 'bg-blue-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const quickPrompts = [
    "Analyze wearable data and identify any concerning trends",
    "How does this patient compare to similar patients?",
    "What do recent research papers say about these symptoms?",
    "Are there any critical alerts I should address?",
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <div className="neo-card p-2 rounded-lg">
          <Bot className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">AI Wearable Analytics</h3>
          <p className="text-xs text-muted-foreground">
            Analyzing data for {patientName}
          </p>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground mb-4">
              Ask me anything about {patientName}'s wearable data
            </p>
            <div className="grid grid-cols-1 gap-2 max-w-md mx-auto">
              {quickPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(prompt)}
                  className="text-xs text-left p-3 neo-card rounded-lg hover:bg-accent transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, idx) => (
              <div key={idx} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] ${message.role === 'user' ? 'ml-auto' : 'mr-auto'}`}>
                  {/* Message bubble */}
                  <div
                    className={`p-3 rounded-lg ${
                      message.role === 'user'
                        ? 'gradient-primary text-white'
                        : 'neo-card'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {/* Analysis results (for assistant messages) */}
                  {message.role === 'assistant' && message.analysis && (
                    <div className="mt-3 space-y-3">
                      {/* Alerts */}
                      {message.analysis.alerts && message.analysis.alerts.length > 0 && (
                        <Card className="p-3 neo-card">
                          <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="h-4 w-4 text-orange-500" />
                            <p className="text-xs font-semibold">
                              Alerts ({message.analysis.alerts.length})
                            </p>
                          </div>
                          <div className="space-y-2">
                            {message.analysis.alerts.slice(0, 3).map((alert, alertIdx) => (
                              <Alert key={alertIdx} className="py-2">
                                <AlertDescription>
                                  <div className="flex items-start gap-2">
                                    <Badge className={getSeverityColor(alert.severity)}>
                                      {alert.severity.toUpperCase()}
                                    </Badge>
                                    <div className="flex-1">
                                      <p className="text-xs font-medium">{alert.message}</p>
                                      <p className="text-xs text-muted-foreground mt-1">
                                        {alert.clinical_significance}
                                      </p>
                                    </div>
                                  </div>
                                </AlertDescription>
                              </Alert>
                            ))}
                          </div>
                        </Card>
                      )}

                      {/* Similar Patients */}
                      {message.analysis.similar_patients && message.analysis.similar_patients.length > 0 && (
                        <Card className="p-3 neo-card">
                          <div className="flex items-center gap-2 mb-2">
                            <Users className="h-4 w-4 text-blue-500" />
                            <p className="text-xs font-semibold">
                              Similar Patients ({message.analysis.similar_patients.length})
                            </p>
                          </div>
                          <div className="space-y-2">
                            {message.analysis.similar_patients.slice(0, 3).map((patient, pIdx) => (
                              <div key={pIdx} className="flex items-center justify-between text-xs">
                                <span>{patient.patient_name}</span>
                                <Badge variant="outline">
                                  {patient.similarity_score}% match
                                </Badge>
                              </div>
                            ))}
                          </div>
                        </Card>
                      )}

                      {/* Research Papers */}
                      {message.analysis.research_papers && message.analysis.research_papers.length > 0 && (
                        <Card className="p-3 neo-card">
                          <div className="flex items-center gap-2 mb-2">
                            <FileText className="h-4 w-4 text-green-500" />
                            <p className="text-xs font-semibold">
                              Research Papers ({message.analysis.research_papers.length})
                            </p>
                          </div>
                          <div className="space-y-2">
                            {message.analysis.research_papers.slice(0, 2).map((paper, pIdx) => (
                              <div key={pIdx} className="text-xs">
                                <p className="font-medium">{paper.title}</p>
                                <p className="text-muted-foreground">{paper.author}</p>
                                {paper.pmc_link && (
                                  <a
                                    href={paper.pmc_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline text-xs"
                                  >
                                    View paper →
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        </Card>
                      )}

                      {/* Recommendations */}
                      {message.analysis.recommendations && message.analysis.recommendations.length > 0 && (
                        <Card className="p-3 neo-card">
                          <div className="flex items-center gap-2 mb-2">
                            <TrendingUp className="h-4 w-4 text-purple-500" />
                            <p className="text-xs font-semibold">Recommendations</p>
                          </div>
                          <ul className="space-y-1">
                            {message.analysis.recommendations.map((rec, rIdx) => (
                              <li key={rIdx} className="text-xs text-muted-foreground flex items-start gap-2">
                                <span className="text-primary">•</span>
                                <span>{rec}</span>
                              </li>
                            ))}
                          </ul>
                        </Card>
                      )}
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground mt-1">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="neo-card p-3 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    <p className="text-sm text-muted-foreground">Analyzing wearable data...</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about wearable data, trends, alerts..."
            className="min-h-[60px] resize-none"
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <Button 
            type="submit" 
            size="icon"
            disabled={!input.trim() || isLoading}
            className="h-[60px] w-[60px]"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}
