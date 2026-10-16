# CI supplies a digest-frozen Go build image; never compile from a floating tag.
ARG GO_IMAGE
FROM ${GO_IMAGE} AS build
WORKDIR /src
COPY go.mod main.go probe.go ./
ARG TARGETOS=linux
ARG TARGETARCH=amd64
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -trimpath -ldflags='-s -w' -o /wingman-app .
FROM scratch
COPY --from=build /wingman-app /wingman-app
USER 65532:65532
EXPOSE 8443
ENTRYPOINT ["/wingman-app"]
