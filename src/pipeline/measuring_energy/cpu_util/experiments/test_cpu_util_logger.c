/*
 * === File Information ===
 * This file is an almost direct copy of "cpu_util_logger.c" but it is setup
 * to be used in experiments. The differences are:
 * - An extra program parameter is included: EXPERIMENT_DURATION_SECONDS,
 * which defines how long the program should run. In contrast to the original,
 * this program will stop after the defined duration, instead of running
 * indefinitely.
 * - The log file format is changed to include work_ns, which is the time
 * it took to perform the work in each interval.
 */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * === Program parameters ===
 */

/*
 * Measurement interval in hertz. I.e. a measurement interval of 100, means
 * we measure every 10ms.
 */
#ifndef HZ
#define HZ 100
#endif
/*
 * Flush interval in sample size. I.e. a flush interval of 100, means we flush
 * every second.
 */
#ifndef FLUSH_INTERVAL
#define FLUSH_INTERVAL 1000
#endif
/*
 *
 */
#ifndef EXPERIMENT_DURATION_SECONDS
#define EXPERIMENT_DURATION_SECONDS 60
#endif

/*
 * === File locations ===
 */
#ifndef PROC_STAT_FILE
#define PROC_STAT_FILE "/proc/stat"
#endif

#ifndef LOG_FILE
#define LOG_FILE "cpu_util_log.csv"
#endif

/*
 * === Start program ===
 */

/*
 * On VMs, /proc/stat can have two additional fields (guest and guest_nice).
 * We read all values, but only use the first 7 for the CPU utilization
 * calculation.
 */
typedef struct proc_stat_times {
  unsigned long user, nice, system, idle, iowait, irq, softirq, steal, guest,
      guest_nice;
} proc_stat_times;

static long long ts_ns(const struct timespec* ts) {
  return (long long)ts->tv_sec * 1000000000LL + ts->tv_nsec;
}

/**
 * read_cpu_times reads the CPU times from /proc/stat and fills the provided
 * proc_stat_times structure. It returns 0 on success and -1 on failure.
 */
static int read_cpu_times(proc_stat_times* times) {
  FILE* fp = fopen(PROC_STAT_FILE, "r");
  if (fp == NULL) {
    perror("Error opening " PROC_STAT_FILE);
    return -1;
  }

  int parameters_read = fscanf(
      fp, "cpu %lu %lu %lu %lu %lu %lu %lu %lu %lu %lu", &times->user,
      &times->nice, &times->system, &times->idle, &times->iowait, &times->irq,
      &times->softirq, &times->steal, &times->guest, &times->guest_nice);

  fclose(fp);

  return parameters_read == 10 ? 0 : -1;
}

/**
 * compute_cpu_utilization computes the CPU utilization percentage between two
 * proc_stat_times structures. This function is based on the cpu-utilization.c
 * file from [Cloud Energy](
 * https://github.com/green-coding-solutions/cloud-energy)
 */
static double compute_cpu_utilization(const proc_stat_times* prev,
                                      const proc_stat_times* curr) {
  unsigned long prev_idle =
      prev->idle + prev->iowait + prev->irq + prev->softirq;
  unsigned long curr_idle =
      curr->idle + curr->iowait + curr->irq + curr->softirq;

  unsigned long prev_compute = prev->user + prev->system + prev->nice;
  unsigned long curr_compute = curr->user + curr->system + curr->nice;

  unsigned long idle_reading = curr_idle - prev_idle;
  unsigned long compute_reading = curr_compute - prev_compute;

  unsigned long divider = compute_reading + idle_reading;
  if (divider == 0) return 0.0;

  double utilization = 100.0 * compute_reading / divider;

  if (utilization < 0.0)
    utilization = 0.0;
  else if (utilization > 100.0)
    utilization = 100.0;

  return utilization;
}

int main() {
  FILE* log_fp = fopen(LOG_FILE, "w");
  if (log_fp == NULL) {
    perror("Error opening log file");
    return 1;
  }

  fprintf(log_fp, "sample,work_ns,cpu_utilization\n");

  long interval_nns = 1000000000L / HZ;

  proc_stat_times prev_times, curr_times;
  if (read_cpu_times(&prev_times) != 0) {
    fprintf(stderr, "Cannot read %s\n", PROC_STAT_FILE);
    fclose(log_fp);
    return 1;
  }

  struct timespec deadline;
  clock_gettime(CLOCK_MONOTONIC, &deadline);

  struct timespec stop_ts = deadline;
  stop_ts.tv_sec += EXPERIMENT_DURATION_SECONDS;

  long sample = 0;
  long expected_samples = (EXPERIMENT_DURATION_SECONDS * HZ);

  while (1) {
    if (sample >= expected_samples) break;

    deadline.tv_nsec += interval_nns;
    if (deadline.tv_nsec >= 1000000000L) {
      deadline.tv_nsec -= 1000000000L;
      deadline.tv_sec++;
    }

    if (deadline.tv_sec > stop_ts.tv_sec) break;

    struct timespec actual;
    clock_gettime(CLOCK_MONOTONIC, &actual);
    if (actual.tv_sec > deadline.tv_sec) {
      // Missed the deadline, skip this measurement and move to the
      // next one.

      // Update prev_times to avoid large jumps in utilization.
      read_cpu_times(&prev_times);

      sample++;
      continue;
    }

    // Sleep until the next measurement time
    clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &deadline, NULL);

    // Measure how late we woke relative to the deadline.
    struct timespec t_wake;
    clock_gettime(CLOCK_MONOTONIC, &t_wake);

    // Silently ignore read errors. File should be readable as seen
    // by initial tests before the measurements started.
    if (read_cpu_times(&curr_times) != 0) continue;

    double utilization = compute_cpu_utilization(&prev_times, &curr_times);
    prev_times = curr_times;

    // Include flushing in the work time.
    if (++sample % FLUSH_INTERVAL == 0) fflush(log_fp);

    struct timespec t_done;
    clock_gettime(CLOCK_MONOTONIC, &t_done);
    long long work_ns = ts_ns(&t_done) - ts_ns(&t_wake);

    fprintf(log_fp, "%ld,%lld,%.2f\n", sample, work_ns, utilization);
  }

  fflush(log_fp);
  fclose(log_fp);
  return 0;
}
