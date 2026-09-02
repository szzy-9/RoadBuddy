import { useEffect, useId, useRef, useState } from 'react'
import type { ChangeEvent, KeyboardEvent } from 'react'
import { searchLocations } from '../api/client'
import type { LocationSuggestion } from '../types/api'

interface AddressAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSelect?: (suggestion: LocationSuggestion) => void
  label: string
  placeholder: string
  /**
   * Treat the initial `value` as an already-chosen suggestion, suppressing the
   * lookup that a prefilled field would otherwise fire on mount.
   */
  initialValueIsSelected?: boolean
}

export default function AddressAutocomplete({
  value,
  onChange,
  onSelect,
  label,
  placeholder,
  initialValueIsSelected = false,
}: AddressAutocompleteProps) {
  const inputId = useId()
  const listboxId = `${inputId}-suggestions`
  const containerRef = useRef<HTMLDivElement | null>(null)
  const requestSequence = useRef(0)
  const selectedLabel = useRef<string | null>(
    initialValueIsSelected && value ? value : null,
  )
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchError, setSearchError] = useState(false)
  const [activeIndex, setActiveIndex] = useState(-1)

  useEffect(() => {
    const handleDocumentMouseDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false)
        setActiveIndex(-1)
      }
    }

    document.addEventListener('mousedown', handleDocumentMouseDown)
    return () => document.removeEventListener('mousedown', handleDocumentMouseDown)
  }, [])

  useEffect(() => {
    const query = value.trim()
    const requestId = ++requestSequence.current

    if (selectedLabel.current === value) {
      selectedLabel.current = null
      setSuggestions([])
      setIsLoading(false)
      setHasSearched(false)
      setSearchError(false)
      return
    }

    if (query.length < 3) {
      setSuggestions([])
      setIsLoading(false)
      setIsOpen(false)
      setHasSearched(false)
      setSearchError(false)
      setActiveIndex(-1)
      return
    }

    setHasSearched(false)
    setSearchError(false)
    const timeoutId = window.setTimeout(async () => {
      setIsLoading(true)
      try {
        const response = await searchLocations(query)
        if (requestId !== requestSequence.current) return
        setSuggestions(response.suggestions.slice(0, 5))
        setHasSearched(true)
        setActiveIndex(-1)
      } catch {
        if (requestId !== requestSequence.current) return
        setSuggestions([])
        setHasSearched(true)
        setSearchError(true)
        setActiveIndex(-1)
      } finally {
        if (requestId === requestSequence.current) {
          setIsLoading(false)
        }
      }
    }, 300)

    return () => window.clearTimeout(timeoutId)
  }, [value])

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    requestSequence.current += 1
    selectedLabel.current = null
    setIsOpen(event.target.value.trim().length >= 3)
    setActiveIndex(-1)
    onChange(event.target.value)
  }

  function selectSuggestion(suggestion: LocationSuggestion) {
    requestSequence.current += 1
    selectedLabel.current = suggestion.label
    setSuggestions([])
    setIsOpen(false)
    setHasSearched(false)
    setSearchError(false)
    setActiveIndex(-1)
    onChange(suggestion.label)
    onSelect?.(suggestion)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      setIsOpen(false)
      setActiveIndex(-1)
      return
    }

    if (!isOpen || suggestions.length === 0) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((current) => (current + 1) % suggestions.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((current) =>
        current <= 0 ? suggestions.length - 1 : current - 1,
      )
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault()
      selectSuggestion(suggestions[activeIndex])
    }
  }

  const showDropdown = isOpen && (
    isLoading || hasSearched || suggestions.length > 0
  )

  return (
    <div className="address-autocomplete" ref={containerRef}>
      <label htmlFor={inputId}><span>{label}</span></label>
      <input
        id={inputId}
        type="text"
        autoComplete="off"
        value={value}
        onChange={handleChange}
        onFocus={() => {
          if (value.trim().length >= 3) setIsOpen(true)
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        maxLength={200}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showDropdown}
        aria-controls={listboxId}
        aria-activedescendant={
          activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined
        }
      />

      {showDropdown && (
        <ul
          id={listboxId}
          className="address-suggestions"
          role="listbox"
          aria-label={`${label} suggestions`}
          aria-busy={isLoading}
        >
          {isLoading ? (
            <li className="address-suggestion-status" role="status">
              Searching Victorian locations…
            </li>
          ) : searchError ? (
            <li className="address-suggestion-status" role="status">
              Address search is temporarily unavailable
            </li>
          ) : suggestions.length === 0 ? (
            <li className="address-suggestion-status" role="status">
              No Victorian locations found
            </li>
          ) : suggestions.map((suggestion, index) => (
            <li key={`${suggestion.label}-${suggestion.longitude}-${suggestion.latitude}`}>
              <button
                id={`${listboxId}-option-${index}`}
                className={`address-suggestion${index === activeIndex ? ' active' : ''}`}
                type="button"
                role="option"
                aria-selected={index === activeIndex}
                tabIndex={-1}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectSuggestion(suggestion)}
              >
                <span aria-hidden="true">⌖</span>
                <span>{suggestion.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
