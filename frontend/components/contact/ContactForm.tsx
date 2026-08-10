"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { CheckCircle2, Mail, MapPin, MessageCircle, Send } from "lucide-react";
import { GlassButton } from "@/components/ui/GlassButton";
import { sendContactMessage } from "@/services/api";
import { useToast } from "@/components/ToastProvider";
import { WHATSAPP_URL } from "@/lib/constants";
import { cn } from "@/lib/cn";

const contactSchema = z.object({
  name: z.string().min(2, "Please enter your name (at least 2 characters)."),
  email: z.string().email("Please enter a valid email address."),
  subject: z.string().min(3, "Please add a short subject."),
  message: z.string().min(10, "Your message should be at least 10 characters."),
});

type ContactFormValues = z.infer<typeof contactSchema>;

const contactChannels = [
  {
    icon: MessageCircle,
    label: "WhatsApp",
    value: "Fastest response",
    href: WHATSAPP_URL,
  },
  {
    icon: Mail,
    label: "Email",
    value: "hello@hdguru.app",
    href: "mailto:hello@hdguru.app",
  },
  {
    icon: MapPin,
    label: "Support hours",
    value: "Mon–Fri · 9am–6pm",
    href: undefined,
  },
];

const inputClasses =
  "glass w-full rounded-2xl px-4 py-3 text-sm text-foreground placeholder:text-foreground/40 focus:outline-none focus:ring-2 focus:ring-primary-500/50 transition-shadow";

export function ContactForm() {
  const { showToast } = useToast();
  const [submittedTicket, setSubmittedTicket] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { name: "", email: "", subject: "", message: "" },
  });

  const onSubmit = async (values: ContactFormValues) => {
    const res = await sendContactMessage(values);
    if (!res.ok || !res.data) {
      showToast(res.error ?? "Something went wrong. Please try again.", "error");
      return;
    }
    setSubmittedTicket(res.data.ticketId);
    reset();
  };

  if (submittedTicket) {
    return (
      <div className="glass-strong rounded-[2rem] p-10 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-500">
          <CheckCircle2 className="h-8 w-8" />
        </div>
        <h2 className="mt-5 text-2xl font-bold text-foreground">
          Message sent!
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-foreground/60">
          Thanks for reaching out. Our team will get back to you within 24
          hours.
        </p>
        <p className="mt-4 inline-flex rounded-full bg-primary-500/10 px-4 py-1.5 text-xs font-semibold text-primary-600 dark:text-primary-300">
          Ticket: {submittedTicket}
        </p>
        <div className="mt-6">
          <GlassButton
            variant="secondary"
            onClick={() => setSubmittedTicket(null)}
          >
            Send another message
          </GlassButton>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="glass rounded-[2rem] p-6 sm:p-10"
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label
              htmlFor="name"
              className="mb-1.5 block text-sm font-semibold text-foreground"
            >
              Name
            </label>
            <input
              id="name"
              type="text"
              placeholder="Your name"
              className={cn(inputClasses, errors.name && "ring-2 ring-rose-500/60")}
              {...register("name")}
            />
            {errors.name && (
              <p className="mt-1.5 text-xs text-rose-500">{errors.name.message}</p>
            )}
          </div>
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block text-sm font-semibold text-foreground"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              className={cn(inputClasses, errors.email && "ring-2 ring-rose-500/60")}
              {...register("email")}
            />
            {errors.email && (
              <p className="mt-1.5 text-xs text-rose-500">{errors.email.message}</p>
            )}
          </div>
        </div>

        <div className="mt-5">
          <label
            htmlFor="subject"
            className="mb-1.5 block text-sm font-semibold text-foreground"
          >
            Subject
          </label>
          <input
            id="subject"
            type="text"
            placeholder="How can we help?"
            className={cn(inputClasses, errors.subject && "ring-2 ring-rose-500/60")}
            {...register("subject")}
          />
          {errors.subject && (
            <p className="mt-1.5 text-xs text-rose-500">{errors.subject.message}</p>
          )}
        </div>

        <div className="mt-5">
          <label
            htmlFor="message"
            className="mb-1.5 block text-sm font-semibold text-foreground"
          >
            Message
          </label>
          <textarea
            id="message"
            rows={5}
            placeholder="Tell us what's on your mind…"
            className={cn(inputClasses, "resize-none", errors.message && "ring-2 ring-rose-500/60")}
            {...register("message")}
          />
          {errors.message && (
            <p className="mt-1.5 text-xs text-rose-500">{errors.message.message}</p>
          )}
        </div>

        <div className="mt-6 flex justify-end">
          <GlassButton type="submit" size="lg" loading={isSubmitting}>
            {isSubmitting ? (
              "Sending…"
            ) : (
              <>
                Send message <Send className="h-4 w-4" />
              </>
            )}
          </GlassButton>
        </div>
      </form>

      <aside className="flex flex-col gap-4">
        {contactChannels.map((channel) => {
          const inner = (
            <>
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-500/20 to-accent-500/20 text-primary-600 dark:text-primary-300">
                <channel.icon className="h-5 w-5" />
              </span>
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {channel.label}
                </p>
                <p className="text-xs text-foreground/50">{channel.value}</p>
              </div>
            </>
          );
          const classes = cn(
            "glass flex items-center gap-3 rounded-3xl p-5 transition-transform hover:-translate-y-0.5",
            channel.href && "cursor-pointer hover:shadow-glow",
          );
          return channel.href ? (
            <a
              key={channel.label}
              href={channel.href}
              target="_blank"
              rel="noopener noreferrer"
              className={classes}
            >
              {inner}
            </a>
          ) : (
            <div key={channel.label} className={classes}>
              {inner}
            </div>
          );
        })}
      </aside>
    </div>
  );
}
