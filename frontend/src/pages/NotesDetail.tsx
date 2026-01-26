import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '@/components/Header';
import { ArrowLeft, FileText, Calendar, Clock, Plus, Edit2, X, Trash2, Search, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDateOnlyForDisplay, getPatientDoctorNotesSummary, getPatientWithNotes, saveDoctorNote, deleteDoctorNote, toLocalDateOnlyString, searchDoctorNotes, DoctorNotesSearchResponse } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Textarea } from '@/components/ui/textarea';

const NotesDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const patientId = id ?? '';
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    data: patient,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['patient', patientId, 'notes'],
    queryFn: () => getPatientWithNotes(patientId),
    enabled: Boolean(patientId),
  });

  const {
    data: patientSummary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    error: summaryError,
  } = useQuery({
    queryKey: ['patient-summary', patientId],
    queryFn: () => getPatientDoctorNotesSummary(patientId, 20),
    enabled: Boolean(patientId),
  });

  const [showNewNote, setShowNewNote] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editNoteContent, setEditNoteContent] = useState('');
  const [searchQuestion, setSearchQuestion] = useState('');
  const [searchResults, setSearchResults] = useState<DoctorNotesSearchResponse[]>([]);
  const [notesPage, setNotesPage] = useState(1);

  const searchLoadingSteps = [
    'Searching notes…',
    'Finding Patient Name',
    'Collecting Visit Notes',
    'Searching Relevant Notes',
    'Summarizing Answer',
  ];

  const [searchLoadingStep, setSearchLoadingStep] = useState(searchLoadingSteps[0]);
  const searchStepIndex = Math.max(0, searchLoadingSteps.indexOf(searchLoadingStep));

  const notesPerPage = 10;
  const doctorNotes = patient?.doctorNotes ?? [];
  const totalNotes = doctorNotes.length;
  const totalPages = Math.max(1, Math.ceil(totalNotes / notesPerPage));
  const safePage = Math.min(Math.max(notesPage, 1), totalPages);
  const startIndex = (safePage - 1) * notesPerPage;
  const pagedNotes = doctorNotes.slice(startIndex, startIndex + notesPerPage);

  useEffect(() => {
    if (notesPage !== safePage) {
      setNotesPage(safePage);
    }
  }, [notesPage, safePage]);

  useEffect(() => {
    setNotesPage(1);
  }, [patientId]);

  const saveMutation = useMutation({
    mutationFn: saveDoctorNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'notes'] });
      toast({
        title: 'Success',
        description: 'Doctor note saved successfully',
      });
      setNewNoteContent('');
      setShowNewNote(false);
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to save doctor note',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDoctorNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId, 'notes'] });
      toast({
        title: 'Success',
        description: 'Doctor note deleted successfully',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to delete doctor note',
        variant: 'destructive',
      });
    },
  });

  const searchMutation = useMutation({
    mutationFn: (question: string) => searchDoctorNotes(patientId, question, patient?.name),
    onMutate: () => {
      setSearchLoadingStep(searchLoadingSteps[0]);
    },
    onSuccess: (data) => {
      setSearchQuestion('');
      setSearchResults((prev) => [data, ...prev]);
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to search doctor notes',
        variant: 'destructive',
      });
    },
  });

  useEffect(() => {
    if (!searchMutation.isPending) {
      setSearchLoadingStep(searchLoadingSteps[0]);
      return;
    }

    let step = 0;
    setSearchLoadingStep(searchLoadingSteps[step]);

    const interval = window.setInterval(() => {
      step = Math.min(step + 1, searchLoadingSteps.length - 1);
      setSearchLoadingStep(searchLoadingSteps[step]);
    }, 1200);

    return () => {
      window.clearInterval(interval);
    };
  }, [searchMutation.isPending, patientId]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">Loading notes…</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Failed to load notes</h1>
          <p className="text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-4">Patient not found</h1>
          <Button onClick={() => navigate('/')}>Return to Dashboard</Button>
        </div>
      </div>
    );
  }

  const handleAddNote = () => {
    if (!newNoteContent.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter note content',
        variant: 'destructive',
      });
      return;
    }

    const noteData = {
      visit_date: toLocalDateOnlyString(new Date()),
      doctor_name: 'Tiffany Mitchell',
      doctor_id: '1',
      visit_notes: newNoteContent.trim(),
      patient_name: patient.name,
      patient_id: patientId,
    };

    saveMutation.mutate(noteData);
  };

  const handleEditNote = (note: any) => {
    setEditingNoteId(note.id);
    setEditNoteContent(note.content);
  };

  const handleSaveEdit = () => {
    if (!editNoteContent.trim()) {
      toast({
        title: 'Error',
        description: 'Please enter note content',
        variant: 'destructive',
      });
      return;
    }

    const noteToEdit = patient?.doctorNotes.find(n => n.id === editingNoteId);
    if (!noteToEdit) {
      toast({
        title: 'Error',
        description: 'Note not found',
        variant: 'destructive',
      });
      return;
    }

    const noteData = {
      visit_date: noteToEdit.date,
      doctor_name: 'Tiffany Mitchell',
      doctor_id: '1',
      visit_notes: editNoteContent.trim(),
      patient_name: patient?.name || '',
      patient_id: patientId,
    };

    saveMutation.mutate(noteData, {
      onSuccess: () => {
        setEditingNoteId(null);
        setEditNoteContent('');
      }
    });
  };

  const handleCancelEdit = () => {
    setEditingNoteId(null);
    setEditNoteContent('');
  };

  const handleDeleteNote = (noteId: string) => {
    if (confirm('Are you sure you want to delete this note? This action cannot be undone.')) {
      deleteMutation.mutate(noteId);
    }
  };

  const handleSearchNotes = () => {
    if (searchQuestion.trim()) {
      searchMutation.mutate(searchQuestion.trim());
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="max-w-4xl mx-auto px-6 py-8">
        <button
          onClick={() => navigate(`/patient/${patient.id}`)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 animate-fade-in"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="text-sm">Back to {patient.name}</span>
        </button>

        <div className="glass-card p-6 mb-6 animate-slide-up">
          <div className="flex items-center gap-3 mb-3">
            <div className="neo-card p-2.5 rounded-xl">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Doctor Notes Summary</h2>
              <p className="text-sm text-muted-foreground">Generated overview for {patient.name}</p>
            </div>
          </div>

          {isSummaryLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Generating summary…</span>
            </div>
          ) : isSummaryError ? (
            <p className="text-sm text-muted-foreground">{(summaryError as Error).message}</p>
          ) : (
            <p className="text-foreground leading-relaxed">{patientSummary?.summary || 'No summary returned.'}</p>
          )}
        </div>

        <div className="glass-card p-8 mb-6 animate-slide-up">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="neo-card p-3 rounded-xl">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground">Doctor's Notes</h1>
                <p className="text-muted-foreground">Clinical notes for {patient.name}</p>
              </div>
            </div>
            <Button onClick={() => setShowNewNote(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Add Note
            </Button>
          </div>

          {showNewNote && (
            <div className="neo-card p-5 rounded-xl mb-6 animate-scale-in">
              <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
                <span className="flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5" />
                  {new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                </span>
              </div>
              <textarea
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Enter your clinical notes here..."
                className="w-full h-32 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none resize-none text-sm leading-relaxed"
              />
              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-border">
                <Button variant="ghost" onClick={() => setShowNewNote(false)}>Cancel</Button>
                <Button onClick={handleAddNote} disabled={saveMutation.isPending}>
                  {saveMutation.isPending ? 'Saving...' : 'Save Note'}
                </Button>
              </div>
            </div>
          )}

          {/* Search Doctor Notes Section */}
          <div className="mt-8 pt-6 border-t border-border relative z-10">
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Search className="h-5 w-5 text-primary" />
              Search Past Visit Notes
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Ask questions about past visits for {patient.name}. For example, "What did I discuss with this patient about medication 2 weeks ago?"
            </p>
            <div className="space-y-4">
              <Textarea
                placeholder="e.g., What did I discuss with this patient about asthma medication?"
                value={searchQuestion}
                onChange={(e) => setSearchQuestion(e.target.value)}
                className="min-h-[100px] resize-none"
                disabled={searchMutation.isPending}
              />
              <Button
                onClick={handleSearchNotes}
                disabled={!searchQuestion.trim() || searchMutation.isPending}
                className="w-full sm:w-auto"
              >
                {searchMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {searchLoadingStep}
                  </>
                ) : (
                  <>
                    <Search className="h-4 w-4 mr-2" />
                    Search Notes
                  </>
                )}
              </Button>
              {searchMutation.isPending && (
                <div className="neo-card p-4 rounded-xl text-left space-y-2">
                  {searchLoadingSteps.map((step, idx) => {
                    const isCurrent = idx === searchStepIndex;
                    const isDone = idx < searchStepIndex;
                    return (
                      <div
                        key={step}
                        className={
                          isCurrent
                            ? 'text-primary font-medium'
                            : isDone
                              ? 'text-foreground/70'
                              : 'text-muted-foreground'
                        }
                      >
                        {step}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Search Results Section */}
          {searchResults.length > 0 && (
            <div className="mt-8 pt-6 border-t border-border space-y-6 relative z-10">
              <h3 className="text-lg font-semibold text-foreground">Search Results</h3>
              {searchResults.map((result, idx) => (
                <div
                  key={idx}
                  className="neo-card p-6 rounded-2xl space-y-4 animate-slide-up"
                >
                  {/* Question */}
                  <div>
                    <p className="text-sm font-medium text-primary mb-2">Question:</p>
                    <p className="text-foreground">{result.question}</p>
                  </div>

                  {/* Answer */}
                  <div>
                    <p className="text-sm font-medium text-primary mb-2">Answer:</p>
                    <div className="space-y-3">
                      {result.answer.split('\n\n').map((paragraph, pIdx) => (
                        <p key={pIdx} className="text-foreground leading-relaxed">
                          {paragraph}
                        </p>
                      ))}
                    </div>
                  </div>

                  {/* Referenced Notes */}
                  {result.notes && result.notes.length > 0 && (
                    <div className="pt-4 border-t border-border/50">
                      <p className="text-sm font-medium text-muted-foreground mb-3">
                        Referenced Visit Notes ({result.notes.length}):
                      </p>
                      <div className="space-y-3">
                        {result.notes.map((note, nIdx) => (
                          <div key={nIdx} className="neo-card p-4 rounded-xl">
                            <div className="flex items-center gap-4 text-xs text-muted-foreground mb-2">
                              <span className="flex items-center gap-1.5">
                                <Calendar className="h-3.5 w-3.5" />
                                {formatDateOnlyForDisplay(note.visit_date)}
                              </span>
                              {note.similarity_score && (
                                <span className="text-primary font-medium">
                                  Relevance: {(note.similarity_score * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-foreground leading-relaxed line-clamp-3">
                              {note.visit_notes}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="mt-12 pt-8 border-t border-border relative z-0">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div className="text-sm text-muted-foreground">
                Showing {totalNotes === 0 ? 0 : startIndex + 1}-{Math.min(startIndex + notesPerPage, totalNotes)} of {totalNotes}
              </div>
              <div className="flex items-center gap-2">
                <div className="text-sm text-muted-foreground">Page {safePage} of {totalPages}</div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setNotesPage((p) => Math.max(1, p - 1))}
                  disabled={safePage <= 1}
                >
                  Prev
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setNotesPage((p) => Math.min(totalPages, p + 1))}
                  disabled={safePage >= totalPages}
                >
                  Next
                </Button>
              </div>
            </div>

            <div className="space-y-4">
              {pagedNotes.map((note, index) => (
                <div
                  key={note.id}
                  className="neo-card p-5 rounded-xl animate-slide-up"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                {editingNoteId === note.id ? (
                  <>
                    <div className="flex items-center gap-4 mb-3 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        {formatDateOnlyForDisplay(note.date)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {note.time}
                      </span>
                    </div>
                    <textarea
                      value={editNoteContent}
                      onChange={(e) => setEditNoteContent(e.target.value)}
                      placeholder="Enter your clinical notes here..."
                      className="w-full h-32 bg-transparent text-foreground placeholder:text-muted-foreground focus:outline-none resize-none text-sm leading-relaxed mb-3"
                    />
                    <div className="flex justify-end gap-3 pt-3 border-t border-border">
                      <Button variant="ghost" size="sm" onClick={handleCancelEdit}>
                        <X className="h-4 w-4 mr-1" />
                        Cancel
                      </Button>
                      <Button size="sm" onClick={handleSaveEdit} disabled={saveMutation.isPending}>
                        {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1.5">
                          <Calendar className="h-3.5 w-3.5" />
                          {formatDateOnlyForDisplay(note.date)}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          {note.time}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditNote(note)}
                          className="h-8"
                        >
                          <Edit2 className="h-3.5 w-3.5 mr-1.5" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteNote(note.id)}
                          className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                          Delete
                        </Button>
                      </div>
                    </div>
                    <p className="text-foreground leading-relaxed">{note.content}</p>
                  </>
                )}
                </div>
              ))}
            </div>

            {patient.doctorNotes.length === 0 && !showNewNote && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No clinical notes recorded yet.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default NotesDetail;
