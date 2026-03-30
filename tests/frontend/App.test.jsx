import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../../frontend/src/App.jsx'

describe('App', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      }),
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders start recording control', () => {
    render(<App />)
    expect(
      screen.getByRole('button', { name: /start recording/i }),
    ).toBeInTheDocument()
  })
})
