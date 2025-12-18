import { Header } from '@/components/Header';
import { useState } from 'react';
import { MessageSquare, Pin, Send, User, Search, PinOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

interface StaffMember {
  id: string;
  name: string;
  role: string;
  avatar: string;
  status: 'online' | 'away' | 'offline';
}

interface Message {
  id: string;
  senderId: string;
  senderName: string;
  content: string;
  timestamp: string;
  isPinned: boolean;
  isPrivate: boolean;
  recipientId?: string;
}

const mockStaff: StaffMember[] = [
  { id: '1', name: 'Dr. Amanda Foster', role: 'Cardiologist', avatar: 'AF', status: 'online' },
  { id: '2', name: 'Nurse Rebecca Adams', role: 'Head Nurse', avatar: 'RA', status: 'online' },
  { id: '3', name: 'Dr. Michael Patel', role: 'Oncologist', avatar: 'MP', status: 'away' },
  { id: '4', name: 'Nurse David Kim', role: 'ICU Nurse', avatar: 'DK', status: 'online' },
  { id: '5', name: 'Dr. Sarah Johnson', role: 'Neurologist', avatar: 'SJ', status: 'offline' },
  { id: '6', name: 'Nurse Emily Chen', role: 'ER Nurse', avatar: 'EC', status: 'online' },
  { id: '7', name: 'Dr. Robert Williams', role: 'General Practitioner', avatar: 'RW', status: 'away' },
];

const mockMessages: Message[] = [
  {
    id: '1',
    senderId: '1',
    senderName: 'Dr. Amanda Foster',
    content: 'Reminder: Monthly staff meeting tomorrow at 9 AM in Conference Room B. Attendance is mandatory.',
    timestamp: '2024-01-15T08:00:00',
    isPinned: true,
    isPrivate: false,
  },
  {
    id: '2',
    senderId: '2',
    senderName: 'Nurse Rebecca Adams',
    content: 'New COVID-19 protocols in effect starting Monday. Please review the updated guidelines in the shared drive.',
    timestamp: '2024-01-14T14:30:00',
    isPinned: true,
    isPrivate: false,
  },
  {
    id: '3',
    senderId: '3',
    senderName: 'Dr. Michael Patel',
    content: 'Can someone cover my rounds this afternoon? I have an emergency consultation.',
    timestamp: '2024-01-15T10:15:00',
    isPinned: false,
    isPrivate: false,
  },
  {
    id: '4',
    senderId: '4',
    senderName: 'Nurse David Kim',
    content: 'Patient in Room 204 needs attention. Vitals are stable but showing slight irregularities.',
    timestamp: '2024-01-15T11:00:00',
    isPinned: false,
    isPrivate: true,
    recipientId: 'current-user',
  },
];

const currentUserId = 'current-user';

export default function Messages() {
  const [messages, setMessages] = useState<Message[]>(mockMessages);
  const [selectedStaff, setSelectedStaff] = useState<StaffMember | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'private'>('all');

  const filteredStaff = mockStaff.filter(staff =>
    staff.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    staff.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pinnedMessages = messages.filter(m => m.isPinned);
  const regularMessages = messages.filter(m => !m.isPinned && (activeTab === 'all' ? !m.isPrivate : m.isPrivate));

  const handleSendMessage = () => {
    if (!newMessage.trim()) return;

    const message: Message = {
      id: Date.now().toString(),
      senderId: currentUserId,
      senderName: 'You',
      content: newMessage,
      timestamp: new Date().toISOString(),
      isPinned: false,
      isPrivate: !!selectedStaff,
      recipientId: selectedStaff?.id,
    };

    setMessages([message, ...messages]);
    setNewMessage('');
    setSelectedStaff(null);
  };

  const togglePin = (messageId: string) => {
    setMessages(messages.map(m =>
      m.id === messageId ? { ...m, isPinned: !m.isPinned } : m
    ));
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="gradient-primary p-2 rounded-xl">
              <MessageSquare className="h-5 w-5 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-semibold text-foreground">Staff Messages</h1>
          </div>
          <p className="text-muted-foreground ml-12">Communicate with healthcare professionals</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Staff Directory */}
          <div className="glass-card neo-shadow rounded-2xl p-5">
            <h2 className="font-medium text-foreground mb-4">Medical Staff</h2>
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search staff..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-muted/50 border-border/50"
              />
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {filteredStaff.map((staff) => (
                <button
                  key={staff.id}
                  onClick={() => setSelectedStaff(selectedStaff?.id === staff.id ? null : staff)}
                  className={cn(
                    "w-full flex items-center gap-3 p-3 rounded-xl transition-all text-left",
                    selectedStaff?.id === staff.id
                      ? "bg-primary/10 border border-primary/30"
                      : "hover:bg-muted/50"
                  )}
                >
                  <div className="relative">
                    <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center text-sm font-medium text-foreground">
                      {staff.avatar}
                    </div>
                    <span
                      className={cn(
                        "absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-background",
                        staff.status === 'online' && "bg-green-500",
                        staff.status === 'away' && "bg-amber-500",
                        staff.status === 'offline' && "bg-muted-foreground"
                      )}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{staff.name}</p>
                    <p className="text-xs text-muted-foreground truncate">{staff.role}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Messages Area */}
          <div className="lg:col-span-2 space-y-6">
            {/* Compose Message */}
            <div className="glass-card neo-shadow rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <h3 className="font-medium text-foreground">
                  {selectedStaff ? `Private message to ${selectedStaff.name}` : 'Broadcast to all staff'}
                </h3>
                {selectedStaff && (
                  <button
                    onClick={() => setSelectedStaff(null)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    (clear)
                  </button>
                )}
              </div>
              <div className="flex gap-3">
                <Textarea
                  placeholder={selectedStaff ? `Message ${selectedStaff.name}...` : "Message all staff..."}
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  className="bg-muted/50 border-border/50 resize-none"
                  rows={2}
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!newMessage.trim()}
                  className="gradient-primary shrink-0"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Pinned Messages */}
            {pinnedMessages.length > 0 && (
              <div className="glass-card neo-shadow rounded-2xl p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Pin className="h-4 w-4 text-primary" />
                  <h3 className="font-medium text-foreground">Pinned Announcements</h3>
                </div>
                <div className="space-y-3">
                  {pinnedMessages.map((message) => (
                    <div
                      key={message.id}
                      className="p-4 rounded-xl bg-primary/5 border border-primary/20"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-foreground">{message.senderName}</span>
                            <span className="text-xs text-muted-foreground">
                              {formatDate(message.timestamp)} at {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm text-foreground/80">{message.content}</p>
                        </div>
                        <button
                          onClick={() => togglePin(message.id)}
                          className="p-1.5 rounded-lg hover:bg-background/50 text-primary"
                        >
                          <PinOff className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Message Tabs & List */}
            <div className="glass-card neo-shadow rounded-2xl p-5">
              <div className="flex items-center gap-4 mb-4 border-b border-border/50 pb-3">
                <button
                  onClick={() => setActiveTab('all')}
                  className={cn(
                    "text-sm font-medium pb-2 border-b-2 transition-colors",
                    activeTab === 'all'
                      ? "text-primary border-primary"
                      : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  All Staff Messages
                </button>
                <button
                  onClick={() => setActiveTab('private')}
                  className={cn(
                    "text-sm font-medium pb-2 border-b-2 transition-colors",
                    activeTab === 'private'
                      ? "text-primary border-primary"
                      : "text-muted-foreground border-transparent hover:text-foreground"
                  )}
                >
                  Private Messages
                </button>
              </div>

              <div className="space-y-3">
                {regularMessages.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No {activeTab === 'private' ? 'private' : ''} messages yet
                  </p>
                ) : (
                  regularMessages.map((message) => (
                    <div
                      key={message.id}
                      className="p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-foreground">{message.senderName}</span>
                            {message.isPrivate && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                Private
                              </span>
                            )}
                            <span className="text-xs text-muted-foreground">
                              {formatDate(message.timestamp)} at {formatTime(message.timestamp)}
                            </span>
                          </div>
                          <p className="text-sm text-foreground/80">{message.content}</p>
                        </div>
                        <button
                          onClick={() => togglePin(message.id)}
                          className="p-1.5 rounded-lg hover:bg-background/50 text-muted-foreground hover:text-primary"
                        >
                          <Pin className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
