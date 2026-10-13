import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authService } from '@/services/auth.service'
import { RegisterForm } from './RegisterForm'

vi.mock('@/services/auth.service', () => ({ authService: { register: vi.fn(), verifyRegistration: vi.fn() } }))

function LoginProbe() {
  return <p>Login page {useLocation().search}</p>
}

function renderForm() {
  const router = createMemoryRouter(
    [
      { path: '/register', element: <RegisterForm /> },
      { path: '/login', element: <LoginProbe /> },
    ],
    { initialEntries: ['/register'] },
  )
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false } } })}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

function fillAndSubmit() {
  const values: Record<string, string> = {
    'Full name': 'Ada Reader',
    Username: 'ada',
    Phone: '+62 812 3456 7890',
    Email: 'ada@example.test',
    Password: 'correct horse',
    'Confirm password': 'correct horse',
  }
  for (const [label, value] of Object.entries(values)) fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }))
}

describe('RegisterForm', () => {
  beforeEach(() => vi.clearAllMocks())

  it('goes back to sign-in when the account is created at once', async () => {
    vi.mocked(authService.register).mockResolvedValue({ data: { message: 'Account created', verificationRequired: false } } as never)
    renderForm()
    fillAndSubmit()

    expect(await screen.findByText('Login page ?registered=1')).toBeInTheDocument()
    expect(authService.register).toHaveBeenCalledWith({
      fullname: 'Ada Reader',
      username: 'ada',
      email: 'ada@example.test',
      phone: '+62 812 3456 7890',
      password: 'correct horse',
    })
  })

  it('asks for the emailed code when the backend verifies emails', async () => {
    vi.mocked(authService.register).mockResolvedValue({ data: { message: 'Email register sent', verificationRequired: true } } as never)
    vi.mocked(authService.verifyRegistration).mockResolvedValue({ data: {} } as never)
    renderForm()
    fillAndSubmit()

    fireEvent.change(await screen.findByLabelText('Verification code'), { target: { value: '123456' } })
    fireEvent.click(screen.getByRole('button', { name: 'Verify and continue' }))

    expect(await screen.findByText('Login page ?registered=1')).toBeInTheDocument()
    expect(authService.verifyRegistration).toHaveBeenCalledWith({ email: 'ada@example.test', otp: '123456' })
  })

  it('lets the user go back from the code step to fix the details', async () => {
    vi.mocked(authService.register).mockResolvedValue({ data: { message: 'Email register sent', verificationRequired: true } } as never)
    renderForm()
    fillAndSubmit()

    fireEvent.click(await screen.findByRole('button', { name: 'Change details or get a new code' }))
    expect(screen.getByLabelText('Email')).toHaveValue('ada@example.test')
  })

  it('refuses a username that looks like a phone number and a password equal to the username', async () => {
    renderForm()
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: '08123456789' } })
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ada@example.test' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'ada@example.test' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('Include at least one letter')).toBeInTheDocument()
    expect(screen.getByText('Do not use your username or email as the password')).toBeInTheDocument()
    expect(authService.register).not.toHaveBeenCalled()
  })

  it('checks that the passwords match', async () => {
    renderForm()
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'correct horse' } })
    fireEvent.change(screen.getByLabelText('Confirm password'), { target: { value: 'different' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('Passwords do not match')).toBeInTheDocument()
    expect(authService.register).not.toHaveBeenCalled()
  })
})
