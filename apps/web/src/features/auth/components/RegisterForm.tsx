import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { useRegister, useVerifyRegistration } from '@/features/auth/hooks/useRegister'
import {
  registerSchema,
  toRegisterPayload,
  verifyCodeSchema,
  type TRegisterFormValues,
  type TVerifyCodeFormValues,
} from '@/features/auth/schemas/register.schema'
import { LOGIN_PATH } from '@/utils/auth-redirect'

const SIGN_IN_AFTER_REGISTER = `${LOGIN_PATH}?registered=1`

const EMPTY: TRegisterFormValues = { fullname: '', username: '', email: '', phone: '', password: '', confirmPassword: '' }

/**
 * Create an account. When the backend verifies emails (default) it mails a 6-digit code and the form asks for it;
 * when it does not (BE_AUTH_EMAIL_VERIFICATION=false) the account exists at once. Either way: back to sign-in.
 */
export function RegisterForm() {
  const navigate = useNavigate()
  const register = useRegister()
  const [codeSentTo, setCodeSentTo] = useState<string | null>(null)
  const form = useForm<TRegisterFormValues>({ resolver: zodResolver(registerSchema), defaultValues: EMPTY })

  const onSubmit = (values: TRegisterFormValues) => {
    register.mutate(toRegisterPayload(values), {
      onSuccess: (result) => {
        if (result.verificationRequired) setCodeSentTo(values.email.trim())
        else navigate(SIGN_IN_AFTER_REGISTER, { replace: true })
      },
    })
  }

  if (codeSentTo) return <VerifyCodeForm email={codeSentTo} onVerified={() => navigate(SIGN_IN_AFTER_REGISTER, { replace: true })} />

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2" noValidate>
        <FormField
          control={form.control}
          name="fullname"
          render={({ field }) => (
            <FormItem className="sm:col-span-2">
              <FormLabel>Full name</FormLabel>
              <FormControl>
                <Input autoComplete="name" autoFocus {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="username"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Username</FormLabel>
              <FormControl>
                <Input autoComplete="username" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="phone"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Phone</FormLabel>
              <FormControl>
                <Input type="tel" autoComplete="tel" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem className="sm:col-span-2">
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" autoComplete="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="new-password" {...field} />
              </FormControl>
              <FormDescription>At least 8 characters.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm password</FormLabel>
              <FormControl>
                <Input type="password" autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {register.error && (
          <p role="alert" className="text-body-sm text-error-bold sm:col-span-2">
            {register.error.message}
          </p>
        )}
        <Button type="submit" disabled={register.isPending} className="sm:col-span-2">
          {register.isPending ? 'Creating account…' : 'Create account'}
        </Button>
        <p className="text-center text-body-sm text-font-secondary sm:col-span-2">
          Already have an account?{' '}
          <Link to={LOGIN_PATH} className="font-semibold text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </Form>
  )
}

function VerifyCodeForm({ email, onVerified }: { email: string; onVerified: () => void }) {
  const verify = useVerifyRegistration()
  const form = useForm<TVerifyCodeFormValues>({ resolver: zodResolver(verifyCodeSchema), defaultValues: { otp: '' } })

  const onSubmit = (values: TVerifyCodeFormValues) => verify.mutate(values.otp.trim(), { onSuccess: onVerified })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
        <p role="status" className="text-body-md text-font-secondary">
          We sent a 6-digit code to <span className="font-semibold text-font-primary">{email}</span>. It expires in 30 minutes.
        </p>
        <FormField
          control={form.control}
          name="otp"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Verification code</FormLabel>
              <FormControl>
                <Input inputMode="numeric" autoComplete="one-time-code" autoFocus maxLength={6} {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {verify.error && (
          <p role="alert" className="text-body-sm text-error-bold">
            {verify.error.message}
          </p>
        )}
        <Button type="submit" disabled={verify.isPending}>
          {verify.isPending ? 'Checking…' : 'Verify and continue'}
        </Button>
      </form>
    </Form>
  )
}
