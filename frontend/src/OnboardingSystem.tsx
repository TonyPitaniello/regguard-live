import { X, ArrowRight, Lightbulb, Users, Zap, BookOpen } from 'lucide-react';
import { useState } from 'react';
import './onboarding-system.css';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  tips: string[];
  voiceCommand?: string;
}

export function OnboardingSystem() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [hasSeenTutorial, setHasSeenTutorial] = useState(
    localStorage.getItem('regguard_tutorial_seen') === 'true'
  );

  const steps: OnboardingStep[] = [
    {
      id: 'welcome',
      title: 'Welcome to RegGuard',
      description: 'Citeable pre-bid punch lists for contractors',
      icon: <Zap size={40} />,
      tips: [
        'Run a free site lookup from the home page',
        'Every punch line shows a source or Unverified',
        'Forward the list to unlock more free lines',
        'Partner $79 · Pro $149 · IC Project PDFs $1,500',
      ],
      voiceCommand: 'Say a site address to start a free lookup',
    },
    {
      id: 'agent',
      title: 'Site diligence lookup',
      description: 'Screen a site before you bid — forward only what you can defend',
      icon: <Lightbulb size={40} />,
      tips: [
        'Enter a US address (deepest coverage: Dallas / Plano / Austin)',
        'Review the top punch-list actions',
        'Forward the list to unlock the full free preview',
        'Upgrade for deep scout research and IC PDFs',
      ],
      voiceCommand: 'Say "go to agent" to open the lookup form',
    },
    {
      id: 'bidweek',
      title: 'Bid-week habit',
      description: 'Save every site you bid this week — re-check before you submit',
      icon: <BookOpen size={40} />,
      tips: [
        'Lookups auto-save to Saved Jobs when you use your email',
        'Open Saved Jobs anytime from the footer or /jobs',
        'Weekly reminder emails nudge you before bid week',
        'Aim for 3+ saved sites in your first two weeks',
      ],
      voiceCommand: 'Say "jobs" to open Saved Jobs',
    },
    {
      id: 'team',
      title: 'Forward & collaborate',
      description: 'Share citeable punch lists with GCs, owners, and estimators',
      icon: <Users size={40} />,
      tips: [
        'Forward punch lists with Source / Unverified intact',
        'Only share what you can defend in a bid file',
        'Federal + state coverage on every ZIP; local packs where curated',
        'Permit runners: start at Partner $79/mo',
      ],
      voiceCommand: 'Say "share" after a lookup to forward results',
    },
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem('regguard_tutorial_seen', 'true');
    setIsOpen(false);
    setHasSeenTutorial(true);
  };

  const step = steps[currentStep];

  if (hasSeenTutorial && !isOpen) {
    return null;
  }

  if (!isOpen) {
    return (
      <button 
        className="onboarding-trigger"
        onClick={() => setIsOpen(true)}
        title="View platform tutorial"
      >
        💡 Tutorial
      </button>
    );
  }
  return (
    <div className="onboarding-overlay">
      <div className="onboarding-modal">
        {/* Header */}
        <div className="onboarding-header">
          <button
            onClick={() => {
              setIsOpen(false);
              handleComplete();
            }}
            className="onboarding-close"
            title="Close tutorial"
          >
            <X size={24} />
          </button>
          <div className="onboarding-progress">
            {steps.map((_, idx) => (
              <div
                key={idx}
                className={`progress-dot ${idx === currentStep ? 'active' : ''} ${
                  idx < currentStep ? 'completed' : ''
                }`}
                onClick={() => setCurrentStep(idx)}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="onboarding-content">
          <div className="onboarding-icon">{step.icon}</div>

          <h2 className="onboarding-title">{step.title}</h2>
          <p className="onboarding-description">{step.description}</p>

          {/* Tips */}
          <div className="onboarding-tips">
            <p className="tips-label">💡 Pro Tips:</p>
            <ul className="tips-list">
              {step.tips.map((tip, idx) => (
                <li key={idx} className="tip-item">
                  <span className="tip-bullet">•</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Voice Command */}
          {step.voiceCommand && (
            <div className="onboarding-voice-hint">
              <Zap size={16} />
              <p>{step.voiceCommand}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="onboarding-footer">
          <button
            onClick={handlePrev}
            className="onboarding-button secondary"
            disabled={currentStep === 0}
          >
            ← Back
          </button>

          <span className="step-indicator">
            {currentStep + 1} / {steps.length}
          </span>

          <button onClick={handleNext} className="onboarding-button primary">
            {currentStep === steps.length - 1 ? (
              <>
                Get Started <ArrowRight size={16} />
              </>
            ) : (
              <>
                Next <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default OnboardingSystem;
