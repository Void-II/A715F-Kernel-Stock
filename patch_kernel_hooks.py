#!/usr/bin/env python3
"""
Manual-hook integration for KernelSU-Next's -legacy branch on non-GKI
kernels (pre-5.10, no ARM64 syscall-wrapper convention).

This patches 4 real kernel files to call into KernelSU-Next's manual
hook handlers directly, since the kprobe/syscall-table hook mode used
by mainline KernelSU-Next requires __arm64_sys_* symbols that only
exist on GKI kernels.

Patched files:
  - fs/exec.c        su -> ksud redirection for execve/execveat
  - fs/open.c        su -> ksud redirection for faccessat
  - fs/stat.c        su -> ksud redirection for stat/newfstatat
  - kernel/reboot.c  supercall channel (ksud <-> kernel IPC), and is
                      also what KernelSU-Next's own build check greps
                      for to confirm manual hooks are wired up at all
"""
import sys

PATCHES = [
    ("fs/exec.c", [
        (
            "static int do_execveat_common(int fd, struct filename *filename,",
            "#ifdef CONFIG_KSU\n"
            "extern int ksu_handle_execveat_sucompat(int *fd, struct filename **filename_ptr,\n"
            "\t\t\t\t\t void *argv, void *envp, int *flags);\n"
            "#endif\n"
            "static int do_execveat_common(int fd, struct filename *filename,",
        ),
        (
            "\tif (IS_ERR(filename))\n"
            "\t\treturn PTR_ERR(filename);\n"
            "\n"
            "\t/*\n"
            "\t * We move the actual failure in case of RLIMIT_NPROC excess from",

            "\tif (IS_ERR(filename))\n"
            "\t\treturn PTR_ERR(filename);\n"
            "\n"
            "#ifdef CONFIG_KSU\n"
            "\tksu_handle_execveat_sucompat(&fd, &filename, NULL, NULL, NULL);\n"
            "#endif\n"
            "\n"
            "\t/*\n"
            "\t * We move the actual failure in case of RLIMIT_NPROC excess from",
        ),
    ]),
    ("fs/open.c", [
        (
            "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n"
            "{\n"
            "\tconst struct cred *old_cred;\n"
            "\tstruct cred *override_cred;\n"
            "\tstruct path path;\n"
            "\tstruct inode *inode;\n"
            "\tstruct vfsmount *mnt;\n"
            "\tint res;\n"
            "\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n"
            "\n"
            "\tif (mode & ~S_IRWXO)\t/* where's F_OK, X_OK, W_OK, R_OK? */\n"
            "\t\treturn -EINVAL;",

            "#ifdef CONFIG_KSU\n"
            "extern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n"
            "\t\t\t\t int *mode, int *flags);\n"
            "#endif\n"
            "\n"
            "SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n"
            "{\n"
            "\tconst struct cred *old_cred;\n"
            "\tstruct cred *override_cred;\n"
            "\tstruct path path;\n"
            "\tstruct inode *inode;\n"
            "\tstruct vfsmount *mnt;\n"
            "\tint res;\n"
            "\tunsigned int lookup_flags = LOOKUP_FOLLOW;\n"
            "\n"
            "#ifdef CONFIG_KSU\n"
            "\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n"
            "#endif\n"
            "\n"
            "\tif (mode & ~S_IRWXO)\t/* where's F_OK, X_OK, W_OK, R_OK? */\n"
            "\t\treturn -EINVAL;",
        ),
    ]),
    ("fs/stat.c", [
        (
            "int vfs_statx(int dfd, const char __user *filename, int flags,\n"
            "\t      struct kstat *stat, u32 request_mask)\n"
            "{\n"
            "\tstruct path path;\n"
            "\tint error = -EINVAL;\n"
            "\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;\n"
            "\n"
            "\tif ((flags & ~(AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT |\n"
            "\t\t       AT_EMPTY_PATH | KSTAT_QUERY_FLAGS)) != 0)\n"
            "\t\treturn -EINVAL;",

            "#ifdef CONFIG_KSU\n"
            "extern int ksu_handle_stat(int *dfd, const char __user **filename_user, int *flags);\n"
            "#endif\n"
            "\n"
            "int vfs_statx(int dfd, const char __user *filename, int flags,\n"
            "\t      struct kstat *stat, u32 request_mask)\n"
            "{\n"
            "\tstruct path path;\n"
            "\tint error = -EINVAL;\n"
            "\tunsigned int lookup_flags = LOOKUP_FOLLOW | LOOKUP_AUTOMOUNT;\n"
            "\n"
            "#ifdef CONFIG_KSU\n"
            "\tksu_handle_stat(&dfd, &filename, &flags);\n"
            "#endif\n"
            "\n"
            "\tif ((flags & ~(AT_SYMLINK_NOFOLLOW | AT_NO_AUTOMOUNT |\n"
            "\t\t       AT_EMPTY_PATH | KSTAT_QUERY_FLAGS)) != 0)\n"
            "\t\treturn -EINVAL;",
        ),
    ]),
    ("kernel/reboot.c", [
        (
            "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n"
            "\t\tvoid __user *, arg)\n"
            "{\n"
            "\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n"
            "\tchar buffer[256];\n"
            "\tint ret = 0;\n"
            "\n"
            "\t/* We only trust the superuser with rebooting the system. */",

            "#ifdef CONFIG_KSU\n"
            "extern int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,\n"
            "\t\t\t\t  void __user **arg);\n"
            "#define KSU_SUPERCALL_MAGIC1 0xDEADBEEF\n"
            "#endif\n"
            "\n"
            "SYSCALL_DEFINE4(reboot, int, magic1, int, magic2, unsigned int, cmd,\n"
            "\t\tvoid __user *, arg)\n"
            "{\n"
            "\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n"
            "\tchar buffer[256];\n"
            "\tint ret = 0;\n"
            "\n"
            "#ifdef CONFIG_KSU\n"
            "\t/* KernelSU-Next supercall channel: only ever triggered by magic1 ==\n"
            "\t * 0xDEADBEEF, a value LINUX_REBOOT_MAGIC1 never equals, so normal\n"
            "\t * reboot/shutdown calls are completely unaffected. */\n"
            "\tif (unlikely(magic1 == KSU_SUPERCALL_MAGIC1))\n"
            "\t\treturn ksu_handle_sys_reboot(magic1, magic2, cmd,\n"
            "\t\t\t\t\t      (void __user **)&arg);\n"
            "#endif\n"
            "\n"
            "\t/* We only trust the superuser with rebooting the system. */",
        ),
    ]),
]

failed = False
for relpath, replacements in PATCHES:
    with open(relpath) as f:
        src = f.read()
    for old, new in replacements:
        if old not in src:
            print(f"ERROR: anchor not found in {relpath}, kernel source may have "
                  f"diverged from what this patch expects. Aborting.", file=sys.stderr)
            print(f"--- expected anchor ---\n{old}", file=sys.stderr)
            failed = True
            continue
        src = src.replace(old, new, 1)
    if not failed:
        with open(relpath, "w") as f:
            f.write(src)
        print(f"{relpath} patched OK")

if failed:
    sys.exit(1)

print("All manual hook patches applied successfully.")
