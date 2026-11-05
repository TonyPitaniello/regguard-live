/**
 * Voice fill mode — one-tap mic fills the free-trial form.
 * NO command menu / NO navigation command list.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Mic, MicOff, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  clearDictationSilenceTimer,
  scheduleDictationSilenceStop,
  type SilenceTimerHandle,
} from './speech-recognition';
import {
  dispatchVoiceFill,
  dispatchVoiceSubmit,
  needsSpokenEmailTip,
  parseVoiceTrialTranscript,
  voiceFieldsReady,
  type VoiceFillFields,
} from './voiceFillParse';

type SpeechRec = SpeechRecognition;

function getSpeechRecognitionCtor(): (new () => SpeechRec) | null {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function formatPhoneChip(digits: string): string {
  if (digits.length !== 10) return digits;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

export function VoiceCommandSystem() {
  const location = useLocation();
  const path = (location.pathname || '/').replace(/\/$/, '') || '/';
  const voiceHomeOnly = path === '/';
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState('');
  const [parsed, setParsed] = useState<VoiceFillFields | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [unsupportedHint, setUnsupportedHint] = useState(false);

  const recognitionRef = useRef<SpeechRec | null>(null);
  const silenceTimerRef = useRef<SilenceTimerHandle>(null);
  const listeningRef = useRef(false);
  const finalBufferRef = useRef('');

  const applyTranscript = useCallback((text: string, finalize: boolean) => {
    const fields = parseVoiceTrialTranscript(text);
    setParsed(fields);
    dispatchVoiceFill(fields);
    if (finalize) {
      setShowConfirm(true);
      document.getElementById('free-trial-form')?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }, []);

  const stopListening = useCallback(() => {
    clearDictationSilenceTimer(silenceTimerRef);
    listeningRef.current = false;
    setIsListening(false);
    try {
      recognitionRef.current?.stop();
    } catch {
      /* already stopped */
    }
  }, []);

  const finishFromSilence = useCallback(() => {
    const text = (finalBufferRef.current || '').trim();
    setIsListening(false);
    listeningRef.current = false;
    if (text) {
      setTranscript(text);
      applyTranscript(text, true);
    } else {
      setError('Didn’t catch that — tap the mic and try again.');
    }
  }, [applyTranscript]);

  useEffect(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      setIsSupported(false);
      return;
    }
    setIsSupported(true);

    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      listeningRef.current = true;
      setIsListening(true);
      setError('');
      setShowConfirm(false);
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = '';
      let finalChunk = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0]?.transcript || '';
        if (event.results[i].isFinal) {
          finalChunk += piece + ' ';
        } else {
          interim += piece;
        }
      }
      if (finalChunk) {
        finalBufferRef.current = (finalBufferRef.current + ' ' + finalChunk).trim();
        setTranscript(finalBufferRef.current);
        applyTranscript(finalBufferRef.current, false);
      }
      setInterimTranscript(interim);
      if (interim) {
        applyTranscript(`${finalBufferRef.current} ${interim}`.trim(), false);
      }

      scheduleDictationSilenceStop({
        timerRef: silenceTimerRef,
        silenceMs: 2200,
        isListening: () => listeningRef.current,
        stopRecognition: () => {
          try {
            recognitionRef.current?.stop();
          } catch {
            /* ignore */
          }
        },
        onSilenceStop: finishFromSilence,
      });
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const code = event.error || 'unknown';
      if (code === 'aborted' || code === 'no-speech') {
        return;
      }
      if (code === 'not-allowed') {
        setError('Microphone blocked — allow mic access in browser settings.');
      } else if (code === 'network') {
        setError('Speech service unavailable. Type the address instead.');
      } else {
        setError(`Voice error: ${code}. You can still type the form.`);
      }
      stopListening();
    };

    recognition.onend = () => {
      clearDictationSilenceTimer(silenceTimerRef);
      if (listeningRef.current) {
        // Unexpected end — treat as finish if we have text
        listeningRef.current = false;
        setIsListening(false);
        const text = finalBufferRef.current.trim();
        if (text) {
          applyTranscript(text, true);
        }
      }
    };

    return () => {
      clearDictationSilenceTimer(silenceTimerRef);
      try {
        recognition.abort();
      } catch {
        /* ignore */
      }
    };
  }, [applyTranscript, finishFromSilence, stopListening]);

  function startListening() {
    if (!recognitionRef.current) return;
    setError('');
    setTranscript('');
    setInterimTranscript('');
    setParsed(null);
    setShowConfirm(false);
    finalBufferRef.current = '';
    try {
      recognitionRef.current.start();
    } catch {
      // Already started
      try {
        recognitionRef.current.stop();
        setTimeout(() => recognitionRef.current?.start(), 200);
      } catch {
        setError('Could not start microphone. Refresh and try again.');
      }
    }
  }

  function toggleListening() {
    if (!isSupported) {
      setUnsupportedHint(true);
      return;
    }
    if (isListening) {
      stopListening();
      const text = finalBufferRef.current.trim();
      if (text) {
        setTranscript(text);
        applyTranscript(text, true);
      }
    } else {
      startListening();
    }
  }

  const toggleRef = useRef(toggleListening);
  toggleRef.current = toggleListening;
  useEffect(() => {
    const onToggle = () => toggleRef.current();
    window.addEventListener('rg-voice-toggle', onToggle);
    return () => window.removeEventListener('rg-voice-toggle', onToggle);
  }, []);

  function handleRunResearch() {
    if (parsed) {
      dispatchVoiceFill(parsed);
    }
    dispatchVoiceSubmit();
    setShowConfirm(false);
  }

  const chips: { label: string; value: string }[] = [];
  if (parsed?.address) chips.push({ label: 'Address', value: parsed.address });
  if (parsed?.city) chips.push({ label: 'City', value: parsed.city });
  if (parsed?.state) chips.push({ label: 'State', value: parsed.state });
  if (parsed?.zip) chips.push({ label: 'ZIP', value: parsed.zip });
  if (parsed?.email) chips.push({ label: 'Email', value: parsed.email });
  if (parsed?.phone) chips.push({ label: 'Phone', value: formatPhoneChip(parsed.phone) });

  const ready = parsed ? voiceFieldsReady(parsed) : false;

  // Mic only on the home free-trial form. On /r, samples, checkout, orders it covers CTAs.
  if (!voiceHomeOnly) {
    return null;
  }

  return (
    <div className="voice-command-system voice-fill-mode">
      <button
        type="button"
        onClick={toggleListening}
        className={`voice-button voice-fill-button ${isListening ? 'listening' : ''}`}
        title={isListening ? 'Tap to stop' : 'Tap to speak your site address'}
        aria-label={isListening ? 'Stop listening' : 'Fill free trial by voice'}
      >
        {isListening ? <Mic size={28} /> : <MicOff size={28} />}
        <span className="voice-status">
          {isListening ? 'Listening…' : 'Speak address'}
        </span>
        {isListening && <span className="voice-pulse-ring" aria-hidden />}
      </button>

      {(isListening || showConfirm || error || unsupportedHint) && (
        <div className="voice-panel voice-fill-panel" role="status" aria-live="polite">
          <div className="voice-header">
            {isListening ? (
              <>
                <span className="listening-dot" />
                <span>Listening — say address, city, state, ZIP, and email</span>
              </>
            ) : showConfirm ? (
              <>
                <CheckCircle2 size={18} className="text-emerald-400" />
                <span>Fields captured</span>
              </>
            ) : (
              <>
                <AlertCircle size={18} />
                <span>Voice fill</span>
              </>
            )}
          </div>

          <div className="voice-transcript">
            <p className="final-text">{transcript || (isListening ? 'Say something like…' : '')}</p>
            {interimTranscript && <p className="interim-text">{interimTranscript}</p>}
            {!transcript && isListening && (
              <p className="interim-text">
                “123 Main Street suite 400 in Austin Texas 78701, email jane at gmail dot com”
              </p>
            )}
          </div>

          {chips.length > 0 && (
            <div className="voice-chips">
              {chips.map((c) => (
                <span key={c.label} className="voice-chip">
                  <strong>{c.label}</strong> {c.value}
                </span>
              ))}
            </div>
          )}

          {showConfirm && parsed && needsSpokenEmailTip(parsed) && (
            <div className="voice-chips">
              <span className="voice-chip voice-chip-tip" role="note">
                Tip: Say email like: jane at gmail dot com
              </span>
            </div>
          )}

          {error && <div className="voice-error">{error}</div>}
          {unsupportedHint && !isSupported && (
            <div className="voice-error">
              Voice fill needs Chrome, Edge, or Safari. Type the form instead — same result.
            </div>
          )}

          {showConfirm && (
            <div className="voice-confirm-actions">
              {ready ? (
                <button type="button" className="voice-run-btn" onClick={handleRunResearch}>
                  Run research
                </button>
              ) : (
                <p className="voice-hint">
                  Need address, city, state, ZIP, and email — tap mic again or finish typing.
                </p>
              )}
              <button type="button" className="voice-close" onClick={() => setShowConfirm(false)}>
                Dismiss
              </button>
            </div>
          )}

          {isListening && (
            <button type="button" className="voice-close" onClick={toggleListening}>
              Stop &amp; fill form
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default VoiceCommandSystem;
